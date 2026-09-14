from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx
import jwt

from app.core.config import settings


SUPPORTED_OIDC_PROVIDERS = ("auth0", "entra", "okta")


class OIDCConfigurationError(RuntimeError):
    pass


class OIDCValidationError(ValueError):
    pass


@dataclass(frozen=True)
class OIDCProviderConfig:
    name: str
    issuer: str
    client_id: str
    audience: str
    discovery_url: str


def _remote_url_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.netloc:
        return True
    if settings.ENV != "production" and parsed.scheme == "http":
        return parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    return False


def get_provider_config(provider: str) -> OIDCProviderConfig:
    provider = provider.lower().strip()
    if provider not in SUPPORTED_OIDC_PROVIDERS:
        raise OIDCConfigurationError("Unsupported OIDC provider")

    prefix = f"OIDC_{provider.upper()}"
    issuer = os.getenv(f"{prefix}_ISSUER", "").strip().rstrip("/")
    client_id = os.getenv(f"{prefix}_CLIENT_ID", "").strip()
    audience = os.getenv(f"{prefix}_AUDIENCE", "").strip() or client_id
    discovery_url = os.getenv(f"{prefix}_DISCOVERY_URL", "").strip()
    if not discovery_url and issuer:
        discovery_url = f"{issuer}/.well-known/openid-configuration"

    if not issuer or not client_id:
        raise OIDCConfigurationError(f"{provider} OIDC provider is not configured")
    if not _remote_url_allowed(issuer) or not _remote_url_allowed(discovery_url):
        raise OIDCConfigurationError("OIDC issuer/discovery URL is not allowed")

    return OIDCProviderConfig(
        name=provider,
        issuer=issuer,
        client_id=client_id,
        audience=audience,
        discovery_url=discovery_url,
    )


class OIDCValidator:
    """Strict OIDC discovery, JWKS and ID-token validator."""

    def __init__(
        self,
        config: OIDCProviderConfig,
        *,
        http_client: httpx.Client | None = None,
    ):
        self.config = config
        self._client = http_client or httpx.Client(
            timeout=5.0,
            follow_redirects=False,
        )
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def discover(self) -> dict[str, Any]:
        try:
            response = self._client.get(self.config.discovery_url)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise OIDCValidationError("OIDC discovery failed") from exc

        discovered_issuer = str(data.get("issuer", "")).rstrip("/")
        if discovered_issuer != self.config.issuer:
            raise OIDCValidationError("OIDC discovery issuer mismatch")

        jwks_uri = str(data.get("jwks_uri", ""))
        authorization_endpoint = str(data.get("authorization_endpoint", ""))
        if not jwks_uri or not _remote_url_allowed(jwks_uri):
            raise OIDCValidationError("OIDC JWKS URI is missing or not allowed")
        if not authorization_endpoint or not _remote_url_allowed(authorization_endpoint):
            raise OIDCValidationError("OIDC authorization endpoint is missing or not allowed")
        return data

    def _jwks(self, jwks_uri: str) -> list[dict[str, Any]]:
        try:
            response = self._client.get(jwks_uri)
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            raise OIDCValidationError("OIDC JWKS retrieval failed") from exc

        keys = payload.get("keys")
        if not isinstance(keys, list) or not keys:
            raise OIDCValidationError("OIDC JWKS contains no signing keys")
        return keys

    def validate_id_token(
        self,
        token: str,
        *,
        nonce: str,
    ) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise OIDCValidationError("Malformed OIDC token") from exc

        if header.get("alg") != "RS256":
            raise OIDCValidationError("OIDC token algorithm is not allowed")
        kid = header.get("kid")
        if not kid:
            raise OIDCValidationError("OIDC token is missing kid")

        discovery = self.discover()
        matching = [
            key
            for key in self._jwks(str(discovery["jwks_uri"]))
            if key.get("kid") == kid and key.get("kty") == "RSA"
        ]
        if len(matching) != 1:
            raise OIDCValidationError("OIDC signing key was not found")

        try:
            signing_key = jwt.PyJWK.from_dict(matching[0]).key
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self.config.audience,
                issuer=self.config.issuer,
                leeway=60,
                options={
                    "require": ["exp", "iat", "iss", "aud", "sub", "nonce"],
                },
            )
        except jwt.PyJWTError as exc:
            raise OIDCValidationError("OIDC token validation failed") from exc

        if claims.get("nonce") != nonce:
            raise OIDCValidationError("OIDC nonce mismatch")

        audience = claims.get("aud")
        if isinstance(audience, list) and len(audience) > 1:
            if claims.get("azp") != self.config.client_id:
                raise OIDCValidationError("OIDC authorized-party mismatch")

        return claims


def login_email(provider: str, claims: dict[str, Any]) -> str:
    """Return the verified bootstrap email for first-time subject binding."""
    provider = provider.lower()
    candidates = [claims.get("email")]
    if provider == "entra":
        candidates.extend([claims.get("preferred_username"), claims.get("upn")])

    email = next(
        (
            str(value).strip().lower()
            for value in candidates
            if isinstance(value, str) and "@" in value
        ),
        "",
    )
    if not email:
        raise OIDCValidationError("OIDC token does not contain a usable login email")

    if provider in {"auth0", "okta"} and claims.get("email_verified") is not True:
        raise OIDCValidationError("OIDC email is not verified")
    return email


def upstream_mfa_satisfied(claims: dict[str, Any]) -> bool:
    amr = claims.get("amr", [])
    if isinstance(amr, str):
        amr = [amr]
    return isinstance(amr, list) and "mfa" in {str(item).lower() for item in amr}
