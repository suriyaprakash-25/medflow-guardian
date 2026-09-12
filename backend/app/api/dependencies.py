from dataclasses import dataclass
from typing import Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, PractitionerProfile
from app.models.hospital import HospitalStaff

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass(frozen=True)
class MFAVerificationContext:
    user: User
    token_type: str


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _load_identity_from_token(
    token: str,
    db: Session,
    *,
    allowed_token_types: Iterable[str],
):
    credentials_exception = _credentials_exception()
    allowed = set(allowed_token_types)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        token_type = payload.get("token_type")
        mfa_verified = payload.get("mfa_verified")
        if not isinstance(email, str) or token_type not in allowed:
            raise credentials_exception
        if token_type == "access" and mfa_verified is not True:
            raise credentials_exception
        if token_type == "preauth" and mfa_verified is not False:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user, token_type


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Resolve a normal authenticated user from a full access token only."""
    user, _ = _load_identity_from_token(
        token,
        db,
        allowed_token_types={"access"},
    )
    return user


def get_mfa_verification_context(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> MFAVerificationContext:
    """Allow only the two token stages intentionally supported by /mfa/verify.

    An access token is accepted only while verifying a newly enrolled MFA secret.
    A pre-auth token is accepted only for an already-enabled MFA login challenge.
    The endpoint performs the final stage-specific check against UserMFA state.
    """
    user, token_type = _load_identity_from_token(
        token,
        db,
        allowed_token_types={"access", "preauth"},
    )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user account",
        )
    return MFAVerificationContext(user=user, token_type=token_type)


def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user account")
    return current_user

def get_practitioner_identity(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Not a practitioner identity")
    return current_user

def get_patient_identity(current_user: User = Depends(get_current_active_user)):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Not a patient identity")
    return current_user

def get_current_organization_context(hospital_id: int, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    membership = db.query(HospitalStaff).filter(
        HospitalStaff.user_id == current_user.id,
        HospitalStaff.hospital_id == hospital_id,
        HospitalStaff.is_active == True
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a valid active member of this organization context")
    return membership

def get_authorization_service(db: Session = Depends(get_db)):
    """FastAPI dependency that provides the Central Authorization Service."""
    from app.services.authorization import AuthorizationService
    return AuthorizationService(db)

def require_authorization(decision_factory):
    """
    Helper to enforce an authorization decision.
    Raises HTTPException 403 with the denial reason if not allowed.
    Use with the authorization service result.
    """
    from app.services.authorization import AuthorizationDecision
    from fastapi import HTTPException
    decision: AuthorizationDecision = decision_factory
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or str(decision.reason))
    return decision