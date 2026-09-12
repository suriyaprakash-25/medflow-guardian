import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.core.limiter import limiter
from app.models.user import User
from app.core.security import get_password_hash

client = TestClient(app)

@pytest.fixture
def rate_limit_user(db_session: Session):
    user = User(
        email="rate_limit@demo.com",
        hashed_password=get_password_hash("password123"),
        role="doctor",
        full_name="Rate Limit Doctor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

def test_login_rate_limiting(db_session: Session, rate_limit_user: User):
    # Temporarily enable rate limiting for this test
    original_enabled = limiter.enabled
    limiter.enabled = True
    
    try:
        # The limit is 5/minute. We will make 6 requests.
        for i in range(5):
            resp = client.post(
                "/api/auth/login",
                data={"username": "rate_limit@demo.com", "password": "password123"}
            )
            assert resp.status_code == 200
        
        # 6th request should fail
        resp = client.post(
            "/api/auth/login",
            data={"username": "rate_limit@demo.com", "password": "password123"}
        )
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]
    finally:
        limiter.enabled = original_enabled
