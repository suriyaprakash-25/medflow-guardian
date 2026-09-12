import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User, PractitionerProfile
from app.core.security import create_access_token

@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def setup_test_data(db):
    # Relies on conftest.py nested transaction rollback to keep DB clean.
    
    # Create User
    doc = User(email="test_doctor_profile@demo.com", hashed_password="pw", role="doctor", full_name="Doc Profile Test", is_active=True)
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return {"doc": doc}

def test_practitioner_profile(db_session):
    data = setup_test_data(db_session)
    client = TestClient(app)

    token = create_access_token("test_doctor_profile@demo.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Get profile (should be 404 initially)
    res_get = client.get("/api/users/practitioner-profile", headers=headers)
    assert res_get.status_code == 404

    # Create profile
    payload = {
        "specialty": "Cardiology",
        "license_number": "MED12345",
        "bio": "Expert in heart health."
    }
    res_post = client.post("/api/users/practitioner-profile", json=payload, headers=headers)
    assert res_post.status_code == 200
    created_profile = res_post.json()
    assert created_profile["specialty"] == "Cardiology"
    assert created_profile["is_verified"] is False

    # Get profile (should now succeed)
    res_get2 = client.get("/api/users/practitioner-profile", headers=headers)
    assert res_get2.status_code == 200
    assert res_get2.json()["license_number"] == "MED12345"

    # Update profile
    payload_update = {
        "specialty": "Neurology",
        "license_number": "MED12345",
        "bio": "Expert in brain health."
    }
    res_post2 = client.post("/api/users/practitioner-profile", json=payload_update, headers=headers)
    assert res_post2.status_code == 200
    assert res_post2.json()["specialty"] == "Neurology"
