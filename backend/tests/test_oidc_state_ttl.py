import jwt

from app.api.oidc import _encode_state, _state_cookie_options
from app.core.config import settings


def test_oidc_state_ttl_is_mfa_tolerant_and_cookie_aligned():
    assert 900 <= settings.OIDC_STATE_TTL_SECONDS <= 3600

    cookie_options = _state_cookie_options()
    assert cookie_options["max_age"] == settings.OIDC_STATE_TTL_SECONDS

    token = _encode_state("okta", "state-value", "nonce-value")
    payload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
    )

    assert payload["exp"] - payload["iat"] == settings.OIDC_STATE_TTL_SECONDS
