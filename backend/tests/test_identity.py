import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_auth_me_unauthorized():
    response = client.get("/api/auth/me")
    assert response.status_code == 401

def test_auth_me_success(db_session):
    from app.models.user import User
    from app.core.security import get_password_hash, create_access_token
    from datetime import timedelta
    
    user = User(
        email="testme@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test Identity",
        role="doctor",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    token = create_access_token(subject=user.email, expires_delta=timedelta(minutes=30))
    
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testme@example.com"
    assert data["system_role"] == "doctor"
    assert "memberships" in data
