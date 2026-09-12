import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import pyotp

from app.main import app
from app.models.user import User
from app.models.auth import UserMFA
from app.core.security import get_password_hash
from app.api.websockets import verify_token

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
    assert "refresh_token" in response.cookies

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me_response.status_code == 200


def test_refresh_token_rotates(db_session: Session, auth_user: User):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    original_refresh = login_resp.cookies.get("refresh_token")
    assert original_refresh is not None

    refresh_resp = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": original_refresh}
    )
    assert refresh_resp.status_code == 200
    new_refresh = refresh_resp.cookies.get("refresh_token")
    assert new_refresh is not None
    assert new_refresh != original_refresh

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

    refresh_resp = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": refresh_token}
    )
    assert refresh_resp.status_code == 401


def test_mfa_pre_auth_token_cannot_access_protected_routes_or_websocket(db_session: Session, auth_user: User):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    access_token = login_resp.json()["access_token"]

    enroll_resp = client.post(
        "/api/auth/mfa/enroll",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert enroll_resp.status_code == 200
    secret = enroll_resp.json()["secret"]

    enable_resp = client.post(
        "/api/auth/mfa/verify",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"code": pyotp.TOTP(secret).now()}
    )
    assert enable_resp.status_code == 200

    mfa_login_resp = client.post(
        "/api/auth/login",
        data={"username": "auth_test@demo.com", "password": "password123"}
    )
    assert mfa_login_resp.status_code == 200
    mfa_data = mfa_login_resp.json()
    assert mfa_data["mfa_required"] is True
    assert mfa_data["token_type"] == "pre-auth"
    pre_auth_token = mfa_data["access_token"]
    assert "refresh_token" not in mfa_login_resp.cookies

    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {pre_auth_token}"},
    )
    assert me_response.status_code == 401

    assert verify_token(pre_auth_token, db_session) is None

    verify_resp = client.post(
        "/api/auth/mfa/verify",
        headers={"Authorization": f"Bearer {pre_auth_token}"},
        json={"code": pyotp.TOTP(secret).now()}
    )
    assert verify_resp.status_code == 200
    final_token = verify_resp.json()["access_token"]
    assert "refresh_token" in verify_resp.cookies

    final_me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {final_token}"},
    )
    assert final_me_response.status_code == 200
    assert verify_token(final_token, db_session) is not None
