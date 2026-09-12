import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import timedelta
from jose import jwt
import pyotp

from app.main import app
from app.models.user import User
from app.models.auth import Session as AuthSession, UserMFA
from app.core.config import settings
from app.core.security import create_access_token, get_password_hash

client = TestClient(app)

@pytest.fixture
def auth_user(db_session: Session):
    user = User(
        email="auth_test@demo.com",
        hashed_password=get_password_hash("password123"),
        role="doctor",
        full_name="Auth Test Doctor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

def test_login_issues_tokens(db_session: Session, auth_user: User):
    response = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["mfa_required"] is False

    claims = jwt.decode(
        data["access_token"], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert claims["token_type"] == "access"
    assert claims["mfa_verified"] is True
    assert "iat" in claims
    
    # Check that refresh cookie was set
    cookies = response.cookies
    assert "refresh_token" in cookies

def test_refresh_token_rotates(db_session: Session, auth_user: User):
    # 1. Login
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    original_refresh = login_resp.cookies.get("refresh_token")
    assert original_refresh is not None

    # 2. Refresh
    refresh_resp = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": original_refresh}
    )
    assert refresh_resp.status_code == 200
    new_data = refresh_resp.json()
    assert "access_token" in new_data
    
    new_refresh = refresh_resp.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != original_refresh

    # 3. Replay attack (using old token)
    replay_resp = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": original_refresh}
    )
    assert replay_resp.status_code == 401

def test_logout_revokes_session(db_session: Session, auth_user: User):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    refresh_token = login_resp.cookies.get("refresh_token")

    logout_resp = client.post(
        "/api/auth/logout",
        cookies={"refresh_token": refresh_token}
    )
    assert logout_resp.status_code == 200

    # Try to refresh with revoked token
    refresh_resp = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 401

def test_mfa_flow(db_session: Session, auth_user: User):
    # Enroll
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    token = login_resp.json()["access_token"]
    
    enroll_resp = client.post(
        "/api/auth/mfa/enroll",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert enroll_resp.status_code == 200
    secret = enroll_resp.json()["secret"]
    
    # Verify to enable
    totp = pyotp.TOTP(secret)
    code = totp.now()
    
    verify_resp = client.post(
        "/api/auth/mfa/verify",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": code}
    )
    assert verify_resp.status_code == 200
    assert "access_token" in verify_resp.json()
    
    # Now try to login again. It should prompt for MFA
    mfa_login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    assert mfa_login_resp.status_code == 200
    mfa_data = mfa_login_resp.json()
    assert mfa_data["mfa_required"] is True
    assert mfa_data["token_type"] == "pre-auth"
    pre_auth_token = mfa_data["access_token"]

    preauth_claims = jwt.decode(
        pre_auth_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
    )
    assert preauth_claims["token_type"] == "preauth"
    assert preauth_claims["mfa_verified"] is False
    
    # A password-stage token cannot act as a normal bearer credential.
    protected_resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {pre_auth_token}"},
    )
    assert protected_resp.status_code == 401

    # Check that this token is missing refresh cookie
    assert "refresh_token" not in mfa_login_resp.cookies

    code2 = pyotp.TOTP(secret).now()

    # Once MFA is enabled, /mfa/verify requires the pre-auth challenge token;
    # a previously issued access token is not a substitute for that stage.
    wrong_stage_resp = client.post(
        "/api/auth/mfa/verify",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": code2},
    )
    assert wrong_stage_resp.status_code == 401
    
    # Complete the MFA login challenge with the pre-auth token.
    verify_resp2 = client.post(
        "/api/auth/mfa/verify",
        headers={"Authorization": f"Bearer {pre_auth_token}"},
        json={"code": code2}
    )
    assert verify_resp2.status_code == 200
    assert "access_token" in verify_resp2.json()
    assert "refresh_token" in verify_resp2.cookies