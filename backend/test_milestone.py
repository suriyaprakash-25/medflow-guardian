import httpx
import os
import sys
from fastapi.testclient import TestClient

# Configure database
from app.core.database import SessionLocal, engine, Base
from app.models.user import User
from app.core.security import get_password_hash
from app.main import app

def seed_users():
    db = SessionLocal()
    # Check if patient exists
    if not db.query(User).filter(User.email == "patient@demo.com").first():
        patient = User(email="patient@demo.com", hashed_password=get_password_hash("password"), role="patient", full_name="Demo Patient")
        db.add(patient)
    if not db.query(User).filter(User.email == "doctor@demo.com").first():
        doctor = User(email="doctor@demo.com", hashed_password=get_password_hash("password"), role="doctor", full_name="Demo Doctor")
        db.add(doctor)
    db.commit()
    db.close()

seed_users()

def test_milestone():
    db = SessionLocal()
    # Ensure hospital exists
    from app.models.hospital import Hospital
    h1 = db.query(Hospital).first()
    if not h1:
        h1 = Hospital(name="Demo Hospital")
        db.add(h1)
        db.commit()
        db.refresh(h1)
        
    client = TestClient(app)

    print("--- Testing Milestone 1 ---")

    # 1. Login Patient
    patient_resp = client.post("/api/auth/login", data={"username": "patient@demo.com", "password": "password"})
    assert patient_resp.status_code == 200, f"Patient login failed: {patient_resp.text}"
    patient_token = patient_resp.json()["access_token"]
    print("Patient logged in.")

    # 2. Login Doctor
    doctor_resp = client.post("/api/auth/login", data={"username": "doctor@demo.com", "password": "password"})
    assert doctor_resp.status_code == 200, f"Doctor login failed: {doctor_resp.text}"
    doctor_token = doctor_resp.json()["access_token"]
    print("Doctor logged in.")

    # 3. Patient submits triage request
    triage_resp = client.post(
        "/api/triage/",
        json={"symptoms": "I have severe chest pain and can't breathe.", "hospital_id": h1.id},
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert triage_resp.status_code == 200, f"Submit failed: {triage_resp.text}"
    triage_data = triage_resp.json()
    print("Patient submitted triage request.")
    print(f"  AI Priority: {triage_data['priority']}")
    print(f"  AI Reasoning: {triage_data['ai_reasoning']}")

    # 4. Doctor retrieves triage requests
    list_resp = client.get(
        "/api/triage/",
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert list_resp.status_code == 200, f"Retrieve failed: {list_resp.text}"
    queue = list_resp.json()
    print("Doctor retrieved triage queue.")
    print(f"  Items in queue: {len(queue)}")
    request_id = queue[0]['id']

    # 5. Doctor updates triage status
    update_resp = client.patch(
        f"/api/triage/{request_id}/status",
        json={"status": "reviewed"},
        headers={"Authorization": f"Bearer {doctor_token}"}
    )
    assert update_resp.status_code == 200, f"Update failed: {update_resp.text}"
    print("Doctor updated request status to 'reviewed'.")

    # 6. Patient retrieves their triage history
    history_resp = client.get(
        "/api/triage/patient",
        headers={"Authorization": f"Bearer {patient_token}"}
    )
    assert history_resp.status_code == 200, f"History fetch failed: {history_resp.text}"
    history = history_resp.json()
    print("Patient retrieved triage history.")
    print(f"  Latest status: {history[0]['status']}")
    assert history[0]['status'] == "reviewed", "Status was not correctly updated for patient"

    print("--- Milestone 2 Verified Successfully! ---")
    db.close()
