import base64
from datetime import datetime, timedelta, timezone

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.services.oidc import (
    OIDCProviderConfig,
    OIDCValidationError,
    OIDCValidator,
    login_email,
)


def _b64url_int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


@pytest.mark.parametrize(
    ("provider", "issuer"),
    [
        ("auth0", "https://tenant.example.auth0.com"),
        ("entra", "https://login.microsoftonline.com/tenant-id/v2.0"),
        ("okta", "https://example.okta.com/oauth2/default"),
    ],
)
def test_provider_discovery_jwks_and_id_token_validation(provider, issuer):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": "test-key",
        "n": _b64url_int(numbers.n),
        "e": _b64url_int(numbers.e),
    }
    discovery_url = f"{issuer}/.well-known/openid-configuration"
    jwks_url = f"{issuer}/keys"
    config = OIDCProviderConfig(
        name=provider,
        issuer=issuer,
        client_id="medflow-client",
        audience="medflow-client",
        discovery_url=discovery_url,
    )

    def handler(request: httpx.Request):
        if str(request.url) == discovery_url:
            return httpx.Response(
                200,
                json={
                    "issuer": issuer,
                    "jwks_uri": jwks_url,
                    "authorization_endpoint": f"{issuer}/authorize",
                },
            )
        if str(request.url) == jwks_url:
            return httpx.Response(200, json={"keys": [jwk]})
        return httpx.Response(404)

    nonce = "nonce-value"
    now = datetime.now(timezone.utc)
    claims = {
        "iss": issuer,
        "aud": "medflow-client",
        "sub": f"{provider}-subject",
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "nonce": nonce,
        "email": "doctor@example.com",
        "email_verified": True,
        "amr": ["pwd", "mfa"],
    }
    token = jwt.encode(
        claims,
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        validated = OIDCValidator(config, http_client=client).validate_id_token(
            token,
            nonce=nonce,
        )

    assert validated["sub"] == f"{provider}-subject"
    assert login_email(provider, validated) == "doctor@example.com"


def test_oidc_rejects_discovery_issuer_substitution():
    issuer = "https://issuer.example.com"
    config = OIDCProviderConfig(
        name="okta",
        issuer=issuer,
        client_id="client",
        audience="client",
        discovery_url=f"{issuer}/.well-known/openid-configuration",
    )

    def handler(request: httpx.Request):
        return httpx.Response(
            200,
            json={
                "issuer": "https://attacker.example.com",
                "jwks_uri": "https://attacker.example.com/keys",
                "authorization_endpoint": "https://attacker.example.com/authorize",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(OIDCValidationError, match="issuer mismatch"):
            OIDCValidator(config, http_client=client).discover()


def test_oidc_rejects_unverified_auth0_email():
    with pytest.raises(OIDCValidationError, match="not verified"):
        login_email(
            "auth0",
            {
                "email": "patient@example.com",
                "email_verified": False,
            },
        )
