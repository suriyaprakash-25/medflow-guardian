import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff
from app.core.security import create_access_token
from datetime import timedelta

client = TestClient(app)

def create_token(email: str):
    return create_access_token(subject=email, expires_delta=timedelta(minutes=15))

def test_patient_cannot_access_admin_dashboard(db_session: Session):
    # Setup patient
    patient = User(email="patient_admin_test@test.com", hashed_password="hashed", role="patient")
    db_session.add(patient)
    db_session.commit()
    
    token = create_token("patient_admin_test@test.com")
    
    # Attempt access
    response = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_doctor_cannot_access_admin_dashboard_without_admin_role(db_session: Session):
    # Setup hospital and doctor
    hospital = Hospital(name="Test Hospital Admin")
    db_session.add(hospital)
    db_session.commit()
    
    doctor = User(email="doctor_admin_test@test.com", hashed_password="hashed", role="doctor")
    db_session.add(doctor)
    db_session.commit()
    
    staff = HospitalStaff(user_id=doctor.id, hospital_id=hospital.id, role="doctor")
    db_session.add(staff)
    db_session.commit()
    
    token = create_token("doctor_admin_test@test.com")
    
    response = client.get(f"/api/admin/dashboard?hospital_id={hospital.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403

def test_org_admin_can_access_dashboard(db_session: Session):
    hospital = Hospital(name="Org Admin Hospital")
    db_session.add(hospital)
    db_session.commit()
    
    org_admin = User(email="org_admin_test@test.com", hashed_password="hashed", role="doctor")
    db_session.add(org_admin)
    db_session.commit()
    
    staff = HospitalStaff(user_id=org_admin.id, hospital_id=hospital.id, role="admin")
    db_session.add(staff)
    db_session.commit()
    
    token = create_token("org_admin_test@test.com")
    
    response = client.get(f"/api/admin/dashboard?hospital_id={hospital.id}", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200

def test_org_admin_cannot_access_other_hospital(db_session: Session):
    h1 = Hospital(name="H1")
    h2 = Hospital(name="H2")
    db_session.add_all([h1, h2])
    db_session.commit()
    
    org_admin = User(email="org_admin_h1@test.com", hashed_password="hashed", role="doctor")
    db_session.add(org_admin)
    db_session.commit()
    
    staff = HospitalStaff(user_id=org_admin.id, hospital_id=h1.id, role="admin")
    db_session.add(staff)
    db_session.commit()
    
    token = create_token("org_admin_h1@test.com")
    
    # Accessing h1 works
    res1 = client.get(f"/api/admin/dashboard?hospital_id={h1.id}", headers={"Authorization": f"Bearer {token}"})
    assert res1.status_code == 200
    
    # Accessing h2 fails
    res2 = client.get(f"/api/admin/dashboard?hospital_id={h2.id}", headers={"Authorization": f"Bearer {token}"})
    print("res2 JSON:", res2.json())
    assert res2.status_code == 403
