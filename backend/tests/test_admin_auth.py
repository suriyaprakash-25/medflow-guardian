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
    patient = User(email="patient_admin_test@test.com", hashed_password="hashed", role="patient")
    db_session.add(patient); db_session.commit()
    response = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {create_token(patient.email)}"})
    assert response.status_code == 403


def test_doctor_cannot_access_admin_dashboard_without_admin_role(db_session: Session):
    hospital = Hospital(name="Test Hospital Admin"); db_session.add(hospital); db_session.commit()
    doctor = User(email="doctor_admin_test@test.com", hashed_password="hashed", role="doctor")
    db_session.add(doctor); db_session.commit()
    db_session.add(HospitalStaff(user_id=doctor.id, hospital_id=hospital.id, role="doctor")); db_session.commit()
    response = client.get(f"/api/admin/dashboard?hospital_id={hospital.id}", headers={"Authorization": f"Bearer {create_token(doctor.email)}"})
    assert response.status_code == 403


def test_org_admin_can_access_dashboard(db_session: Session):
    hospital = Hospital(name="Org Admin Hospital"); db_session.add(hospital); db_session.commit()
    admin = User(email="org_admin_test@test.com", hashed_password="hashed", role="doctor")
    db_session.add(admin); db_session.commit()
    db_session.add(HospitalStaff(user_id=admin.id, hospital_id=hospital.id, role="admin")); db_session.commit()
    response = client.get(f"/api/admin/dashboard?hospital_id={hospital.id}", headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 200


def test_org_admin_cannot_access_other_hospital(db_session: Session):
    h1 = Hospital(name="H1"); h2 = Hospital(name="H2"); db_session.add_all([h1, h2]); db_session.commit()
    admin = User(email="org_admin_h1@test.com", hashed_password="hashed", role="doctor")
    db_session.add(admin); db_session.commit()
    db_session.add(HospitalStaff(user_id=admin.id, hospital_id=h1.id, role="admin")); db_session.commit()
    token = create_token(admin.email)
    assert client.get(f"/api/admin/dashboard?hospital_id={h1.id}", headers={"Authorization": f"Bearer {token}"}).status_code == 200
    assert client.get(f"/api/admin/dashboard?hospital_id={h2.id}", headers={"Authorization": f"Bearer {token}"}).status_code == 403


def test_platform_admin_can_create_org(db_session: Session):
    admin = User(email="platform@test.com", hashed_password="hashed", role="platform_admin")
    db_session.add(admin); db_session.commit()
    response = client.post("/api/admin/organization", json={"name": "New Org"}, headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 200
    assert response.json()["name"] == "New Org"


def test_org_admin_cannot_create_org(db_session: Session):
    h1 = Hospital(name="H1"); db_session.add(h1); db_session.commit()
    admin = User(email="org_admin_create@test.com", hashed_password="hashed", role="doctor")
    db_session.add(admin); db_session.commit()
    db_session.add(HospitalStaff(user_id=admin.id, hospital_id=h1.id, role="admin")); db_session.commit()
    response = client.post("/api/admin/organization", json={"name": "New Org"}, headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 403


def test_org_admin_can_provision_existing_staff_in_own_org(db_session: Session):
    h1 = Hospital(name="H1"); db_session.add(h1); db_session.commit()
    admin = User(email="org_admin_staff@test.com", hashed_password="hashed", role="doctor")
    new_user = User(email="new_staff@test.com", hashed_password="hashed", role="doctor")
    db_session.add_all([admin, new_user]); db_session.commit()
    db_session.add(HospitalStaff(user_id=admin.id, hospital_id=h1.id, role="admin")); db_session.commit()
    response = client.post(f"/api/admin/staff?hospital_id={h1.id}", json={"email": new_user.email, "role": "doctor"}, headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 200
    assert "membership_id" in response.json()


def test_new_staff_account_requires_explicit_password(db_session: Session):
    h1 = Hospital(name="Password Policy Hospital"); db_session.add(h1); db_session.commit()
    admin = User(email="org_admin_password@test.com", hashed_password="hashed", role="doctor")
    db_session.add(admin); db_session.commit()
    db_session.add(HospitalStaff(user_id=admin.id, hospital_id=h1.id, role="admin")); db_session.commit()
    response = client.post(f"/api/admin/staff?hospital_id={h1.id}", json={"email": "fresh_staff@test.com", "role": "doctor"}, headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 400
    assert "password is required" in response.json()["detail"]


def test_org_admin_cannot_provision_staff_in_other_org(db_session: Session):
    h1 = Hospital(name="H1"); h2 = Hospital(name="H2"); db_session.add_all([h1, h2]); db_session.commit()
    admin = User(email="org_admin_cross@test.com", hashed_password="hashed", role="doctor")
    db_session.add(admin); db_session.commit()
    db_session.add(HospitalStaff(user_id=admin.id, hospital_id=h1.id, role="admin")); db_session.commit()
    response = client.post(f"/api/admin/staff?hospital_id={h2.id}", json={"email": "hacker@test.com", "role": "admin", "password": "strong-password-123"}, headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 403


def test_platform_admin_can_provision_new_staff_with_explicit_password(db_session: Session):
    hospital = Hospital(name="Platform Staff Hospital"); db_session.add(hospital); db_session.commit()
    admin = User(email="platform_staff@test.com", hashed_password="hashed", role="platform_admin")
    db_session.add(admin); db_session.commit()
    response = client.post(f"/api/admin/staff?hospital_id={hospital.id}", json={"email": "new_platform_staff@test.com", "full_name": "New Doctor", "password": "strong-password-123", "role": "doctor"}, headers={"Authorization": f"Bearer {create_token(admin.email)}"})
    assert response.status_code == 200
    created = db_session.query(User).filter(User.email == "new_platform_staff@test.com").one()
    assert created.full_name == "New Doctor"
    assert created.hashed_password != "strong-password-123"
