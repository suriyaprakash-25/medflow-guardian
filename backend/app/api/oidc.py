from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import MFAResponse, _issue_tokens
from app.core.config import settings
from app.core.database import get_db
from app.models.auth import UserMFA
from app.models.oidc import OIDCIdentity
from app.models.user import User
from app.services.oidc import (
    OIDCConfigurationError,
    OIDCValidationError,
    OIDCValidator,
    SUPPORTED_OIDC_PROVIDERS,
    get_provider_config,
    login_email,
    upstream_mfa_satisfied,
)


router = APIRouter()
_STATE_COOKIE = "medflow_oidc_state"


class OIDCExchangeRequest(BaseModel):
    id_token: str = Field(min_length=32, max_length=16384)
    state: str = Field(min_length=32, max_length=256)


def _state_cookie_options() -> dict:
    return {
        "httponly": True,
        "secure": settings.ENV == "production",
        "samesite": "lax",
        "max_age": settings.OIDC_STATE_TTL_SECONDS,
        "path": "/api/auth/oidc",
    }


def _encode_state(provider: str, state: str, nonce: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "typ": "oidc_state",
            "provider": provider,
            "state": state,
            "nonce": nonce,
            "iat": now,
            "exp": now + timedelta(seconds=settings.OIDC_STATE_TTL_SECONDS),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def _decode_state(raw_cookie: str, provider: str, state: str) -> str:
    try:
        payload = jwt.decode(
            raw_cookie,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "iat", "provider", "state", "nonce", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="OIDC login state is invalid or expired") from exc

    if (
        payload.get("typ") != "oidc_state"
        or payload.get("provider") != provider
        or not secrets.compare_digest(str(payload.get("state", "")), state)
    ):
        raise HTTPException(status_code=401, detail="OIDC login state mismatch")
    return str(payload["nonce"])


def _provider_or_404(provider: str):
    try:
        return get_provider_config(provider)
    except OIDCConfigurationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/providers")
def oidc_providers():
    enabled = []
    for provider in SUPPORTED_OIDC_PROVIDERS:
        try:
            config = get_provider_config(provider)
        except OIDCConfigurationError:
            continue
        enabled.append(
            {
                "provider": provider,
                "issuer": config.issuer,
                "client_id": config.client_id,
            }
        )
    return {"providers": enabled}


@router.post("/{provider}/challenge")
def oidc_challenge(provider: str, response: Response):
    config = _provider_or_404(provider)
    validator = OIDCValidator(config)
    try:
        discovery = validator.discover()
    except OIDCValidationError as exc:
        raise HTTPException(status_code=503, detail="OIDC provider discovery unavailable") from exc
    finally:
        validator.close()

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    response.set_cookie(
        _STATE_COOKIE,
        _encode_state(config.name, state, nonce),
        **_state_cookie_options(),
    )
    return {
        "provider": config.name,
        "issuer": config.issuer,
        "client_id": config.client_id,
        "authorization_endpoint": discovery.get("authorization_endpoint"),
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
    }


@router.post("/{provider}/exchange", response_model=MFAResponse)
def oidc_exchange(
    provider: str,
    exchange: OIDCExchangeRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    config = _provider_or_404(provider)
    state_cookie = request.cookies.get(_STATE_COOKIE)
    if not state_cookie:
        raise HTTPException(status_code=401, detail="OIDC login state cookie is required")

    nonce = _decode_state(state_cookie, config.name, exchange.state)
    validator = OIDCValidator(config)
    try:
        claims = validator.validate_id_token(exchange.id_token, nonce=nonce)
    except OIDCValidationError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    finally:
        validator.close()

    subject = str(claims["sub"])
    identity = (
        db.query(OIDCIdentity)
        .filter(
            OIDCIdentity.provider == config.name,
            OIDCIdentity.issuer == config.issuer,
            OIDCIdentity.subject == subject,
        )
        .first()
    )

    if identity is None:
        try:
            email = login_email(config.name, claims)
        except OIDCValidationError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc

        user = (
            db.query(User)
            .filter(func.lower(User.email) == email)
            .first()
        )
        if not user or not user.is_active:
            raise HTTPException(
                status_code=403,
                detail="Federated identity is not linked to an active MedFlow account",
            )

        identity = OIDCIdentity(
            user_id=user.id,
            provider=config.name,
            issuer=config.issuer,
            subject=subject,
            last_login_at=datetime.now(timezone.utc),
        )
        db.add(identity)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            identity = (
                db.query(OIDCIdentity)
                .filter(
                    OIDCIdentity.provider == config.name,
                    OIDCIdentity.issuer == config.issuer,
                    OIDCIdentity.subject == subject,
                )
                .first()
            )
            if identity is None:
                raise HTTPException(
                    status_code=409,
                    detail="OIDC identity binding conflict",
                )
            user = db.query(User).filter(User.id == identity.user_id).first()
    else:
        user = db.query(User).filter(User.id == identity.user_id).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="Federated MedFlow account is inactive")

    mfa_record = (
        db.query(UserMFA)
        .filter(UserMFA.user_id == user.id, UserMFA.is_enabled == True)
        .first()
    )
    if mfa_record and not upstream_mfa_satisfied(claims):
        raise HTTPException(
            status_code=403,
            detail="Upstream OIDC token does not satisfy the account MFA requirement",
        )

    identity.last_login_at = datetime.now(timezone.utc)
    response.delete_cookie(
        _STATE_COOKIE,
        path="/api/auth/oidc",
        secure=settings.ENV == "production",
        httponly=True,
        samesite="lax",
    )
    return _issue_tokens(db, response, user)
