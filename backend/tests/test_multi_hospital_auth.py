import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.triage import TriageRequest
from app.core.security import create_access_token

@pytest.fixture(scope="module")
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def setup_test_data(db):
    # Clear existing test data
    db.query(TriageRequest).delete()
    db.query(Visit).delete()
    db.query(HospitalStaff).delete()
    db.query(Hospital).delete()
    db.query(User).filter(User.email.like("test_%@demo.com")).delete()
    db.commit()

    # Create Hospitals
    h1 = Hospital(name="Test Hospital A")
    h2 = Hospital(name="Test Hospital B")
    db.add(h1)
    db.add(h2)
    db.commit()
    db.refresh(h1)
    db.refresh(h2)

    # Create Users
    doc_a = User(email="test_doc_a@demo.com", hashed_password="pw", role="doctor", full_name="Doc A", is_active=True)
    doc_b = User(email="test_doc_b@demo.com", hashed_password="pw", role="doctor", full_name="Doc B", is_active=True)
    doc_ab = User(email="test_doc_ab@demo.com", hashed_password="pw", role="doctor", full_name="Doc AB", is_active=True)
    doc_inactive = User(email="test_doc_inactive@demo.com", hashed_password="pw", role="doctor", full_name="Doc Inactive", is_active=True)
    patient = User(email="test_patient@demo.com", hashed_password="pw", role="patient", full_name="Patient", is_active=True)
    
    db.add_all([doc_a, doc_b, doc_ab, doc_inactive, patient])
    db.commit()
    for u in [doc_a, doc_b, doc_ab, doc_inactive, patient]:
        db.refresh(u)

    # Memberships
    db.add(HospitalStaff(user_id=doc_a.id, hospital_id=h1.id, is_active=True))
    db.add(HospitalStaff(user_id=doc_b.id, hospital_id=h2.id, is_active=True))
    db.add(HospitalStaff(user_id=doc_ab.id, hospital_id=h1.id, is_active=True))
    db.add(HospitalStaff(user_id=doc_ab.id, hospital_id=h2.id, is_active=True))
    db.add(HospitalStaff(user_id=doc_inactive.id, hospital_id=h1.id, is_active=False)) # Inactive
    db.commit()

    return {
        "h1": h1, "h2": h2,
        "doc_a": doc_a, "doc_b": doc_b, "doc_ab": doc_ab, "doc_inactive": doc_inactive,
        "patient": patient
    }

def test_triage_isolation():
    db = SessionLocal()
    data = setup_test_data(db)
    client = TestClient(app)

    patient_token = create_access_token("test_patient@demo.com")
    
    # Patient submits triage to Hospital A
    res_a = client.post("/api/triage/", 
        json={"symptoms": "Headache A", "hospital_id": data["h1"].id}, 
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert res_a.status_code == 200

    # Patient submits triage to Hospital B
    res_b = client.post("/api/triage/", 
        json={"symptoms": "Cough B", "hospital_id": data["h2"].id}, 
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert res_b.status_code == 200

    # Doctor A checks Triage (Should only see Hospital A)
    doc_a_token = create_access_token("test_doc_a@demo.com")
    res_doc_a = client.get("/api/triage/", headers={"Authorization": f"Bearer {doc_a_token}"})
    assert res_doc_a.status_code == 200
    triage_a = res_doc_a.json()
    assert len(triage_a) == 1
    assert triage_a[0]["hospital_id"] == data["h1"].id

    # Doctor B checks Triage (Should only see Hospital B)
    doc_b_token = create_access_token("test_doc_b@demo.com")
    res_doc_b = client.get("/api/triage/", headers={"Authorization": f"Bearer {doc_b_token}"})
    assert res_doc_b.status_code == 200
    triage_b = res_doc_b.json()
    assert len(triage_b) == 1
    assert triage_b[0]["hospital_id"] == data["h2"].id

    # Doctor AB checks Triage (Should see both)
    doc_ab_token = create_access_token("test_doc_ab@demo.com")
    res_doc_ab = client.get("/api/triage/", headers={"Authorization": f"Bearer {doc_ab_token}"})
    assert res_doc_ab.status_code == 200
    assert len(res_doc_ab.json()) == 2

    # Inactive Doctor checks Triage (Should see empty)
    doc_inactive_token = create_access_token("test_doc_inactive@demo.com")
    res_doc_inactive = client.get("/api/triage/", headers={"Authorization": f"Bearer {doc_inactive_token}"})
    assert res_doc_inactive.status_code == 200
    assert len(res_doc_inactive.json()) == 0

    # Update Triage: Doctor B attempts to update Triage A (Should fail)
    res_fail = client.patch(f"/api/triage/{res_a.json()['id']}/status",
        json={"status": "reviewed"},
        headers={"Authorization": f"Bearer {doc_b_token}"}
    )
    assert res_fail.status_code == 403

    db.close()

def test_websocket_isolation():
    db = SessionLocal()
    data = setup_test_data(db)

    # Setup clients
    doc_a_token = create_access_token("test_doc_a@demo.com")
    doc_b_token = create_access_token("test_doc_b@demo.com")
    patient_token = create_access_token("test_patient@demo.com")

    client = TestClient(app)
    
    with client.websocket_connect(f"/api/ws?token={doc_a_token}") as ws_a:
        with client.websocket_connect(f"/api/ws?token={doc_b_token}") as ws_b:
            # Patient submits to Hospital A
            res_a = client.post("/api/triage/", 
                json={"symptoms": "Emergency A", "hospital_id": data["h1"].id}, 
                headers={"Authorization": f"Bearer {patient_token}"}
            )
            assert res_a.status_code == 200

            # Doc A should receive it
            msg_a = ws_a.receive_json()
            assert msg_a["type"] == "triage_update"
            assert msg_a["data"]["hospital_id"] == data["h1"].id

            # Doc B should NOT receive it
            res_b = client.post("/api/triage/", 
                json={"symptoms": "Emergency B", "hospital_id": data["h2"].id}, 
                headers={"Authorization": f"Bearer {patient_token}"}
            )
            assert res_b.status_code == 200

            msg_b = ws_b.receive_json()
            assert msg_b["type"] == "triage_update"
            assert msg_b["data"]["hospital_id"] == data["h2"].id

    db.close()
