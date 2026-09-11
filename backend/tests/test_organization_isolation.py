import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff
from app.core.security import get_password_hash, create_access_token
from datetime import timedelta

client = TestClient(app)

def test_hospital_isolation(db_session):
    # Setup Hospital A and Hospital B
    hosp_a = Hospital(name="Hospital A")
    hosp_b = Hospital(name="Hospital B")
    db_session.add(hosp_a)
    db_session.add(hosp_b)
    db_session.commit()

    # Setup Doctor who belongs ONLY to Hospital A
    doc_a = User(
        email="doc_a@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Doctor A",
        role="doctor",
        is_active=True
    )
    db_session.add(doc_a)
    db_session.commit()

    staff_a = HospitalStaff(
        user_id=doc_a.id,
        hospital_id=hosp_a.id,
        role="doctor",
        is_active=True
    )
    db_session.add(staff_a)
    db_session.commit()

    token = create_access_token(subject=doc_a.email, expires_delta=timedelta(minutes=30))
    
    # Doctor A requesting access on behalf of Hospital B should FAIL
    response = client.post(
        "/api/access-requests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "patient_id": 1,
            "hospital_id": hosp_b.id,
            "document_ids": [1],
            "reason": "Need records"
        }
    )
    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]
