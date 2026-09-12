from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from jose import jwt
from starlette.websockets import WebSocketDisconnect

from app.api.websockets import WS_AUTH_PROTOCOL, manager
from app.core.config import settings
from app.core.limiter import get_real_ip
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.auth import RefreshTokenHistory, Session as AuthSession
from app.models.notification import Notification
from app.models.user import User


client = TestClient(app)


def _create_user(db_session, *, email: str, role: str = "patient") -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("password123"),
        role=role,
        full_name="R8 Test User",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _request(peer: str, forwarded_for: str | None = None) -> Request:
    headers = []
    if forwarded_for is not None:
        headers.append((b"x-forwarded-for", forwarded_for.encode("ascii")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "GET",
            "scheme": "https",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": headers,
            "client": (peer, 12345),
            "server": ("testserver", 443),
        }
    )


def test_refresh_replay_revokes_current_token_family(db_session):
    user = _create_user(db_session, email="r8-replay@demo.com", role="doctor")

    login = client.post(
        "/api/auth/login",
        data={"username": user.email, "password": "password123"},
    )
    assert login.status_code == 200
    first_refresh = login.cookies.get("refresh_token")
    assert first_refresh

    rotated = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": first_refresh},
    )
    assert rotated.status_code == 200
    second_refresh = rotated.cookies.get("refresh_token")
    assert second_refresh and second_refresh != first_refresh

    history = db_session.query(RefreshTokenHistory).filter(
        RefreshTokenHistory.user_id == user.id
    ).one()
    active_session = db_session.query(AuthSession).filter(
        AuthSession.user_id == user.id
    ).one()
    assert history.token_family == active_session.token_family
    assert active_session.revoked_at is None

    replay = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": first_refresh},
    )
    assert replay.status_code == 401

    db_session.refresh(active_session)
    assert active_session.revoked_at is not None

    current_after_replay = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": second_refresh},
    )
    assert current_after_replay.status_code == 401


def test_websocket_rejects_query_string_bearer_token(db_session):
    user = _create_user(db_session, email="r8-ws-query@demo.com")
    token = create_access_token(user.email)

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(f"/ws?token={token}"):
            pass

    assert exc.value.code == 1008


def test_websocket_accepts_subprotocol_bearer_without_echoing_token(db_session):
    user = _create_user(db_session, email="r8-ws-protocol@demo.com")
    token = create_access_token(user.email)

    with client.websocket_connect(
        "/ws",
        subprotocols=[WS_AUTH_PROTOCOL, token],
    ) as websocket:
        assert websocket.accepted_subprotocol == WS_AUTH_PROTOCOL
        assert websocket.accepted_subprotocol != token


def test_websocket_rejects_mfa_preauth_token(db_session):
    user = _create_user(db_session, email="r8-ws-preauth@demo.com")
    token = create_access_token(
        user.email,
        expires_delta=timedelta(minutes=2),
        token_type="preauth",
        mfa_verified=False,
    )

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws",
            subprotocols=[WS_AUTH_PROTOCOL, token],
        ):
            pass

    assert exc.value.code == 1008


def test_websocket_rejects_expired_access_token(db_session):
    user = _create_user(db_session, email="r8-ws-expired@demo.com")
    expired = jwt.encode(
        {
            "sub": user.email,
            "token_type": "access",
            "mfa_verified": True,
            "exp": datetime.now(timezone.utc) - timedelta(seconds=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/ws",
            subprotocols=[WS_AUTH_PROTOCOL, expired],
        ):
            pass

    assert exc.value.code == 1008


def test_websocket_event_authorization_defaults_deny_and_binds_notification_recipient(
    db_session, monkeypatch
):
    recipient = _create_user(db_session, email="r8-notification-owner@demo.com")
    other = _create_user(db_session, email="r8-notification-other@demo.com")
    notification = Notification(
        user_id=recipient.id,
        type="security_test",
        message="Recipient-bound event",
    )
    db_session.add(notification)
    db_session.commit()
    db_session.refresh(notification)

    class SessionProxy:
        def __init__(self, session):
            self._session = session

        def __getattr__(self, name):
            return getattr(self._session, name)

        def close(self):
            # The test fixture owns the transactional session lifecycle.
            return None

    monkeypatch.setattr(
        "app.core.database.SessionLocal",
        lambda: SessionProxy(db_session),
    )

    assert manager._evaluate_message_authorization(
        {"type": "unknown", "data": {}},
        recipient.id,
        delivery_scope="personal",
    ) is False
    assert manager._evaluate_message_authorization(
        {"type": "notification_created", "data": {}},
        recipient.id,
        delivery_scope="personal",
    ) is False
    assert manager._evaluate_message_authorization(
        {
            "type": "notification_created",
            "data": {"notification_id": notification.id},
        },
        recipient.id,
        delivery_scope="personal",
    ) is True
    assert manager._evaluate_message_authorization(
        {
            "type": "notification_created",
            "data": {"notification_id": notification.id},
        },
        other.id,
        delivery_scope="personal",
    ) is False


def test_rate_limit_ignores_forwarded_header_from_untrusted_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/8"])
    request = _request("203.0.113.10", "198.51.100.44")

    assert get_real_ip(request) == "203.0.113.10"


def test_rate_limit_uses_nearest_untrusted_hop_behind_trusted_proxies(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/8"])
    request = _request("10.0.0.9", "198.51.100.44, 10.0.0.8")

    assert get_real_ip(request) == "198.51.100.44"


def test_rate_limit_malformed_forwarded_chain_falls_back_to_peer(monkeypatch):
    monkeypatch.setattr(settings, "TRUSTED_PROXY_CIDRS", ["10.0.0.0/8"])
    request = _request("10.0.0.9", "198.51.100.44, not-an-ip")

    assert get_real_ip(request) == "10.0.0.9"