"""P0 regression tests for patient-owned history endpoints.

These tests protect against horizontal IDOR on visit and appointment history.
The patient-scoped routes must never treat a path-supplied patient ID as authority,
and practitioners must use practitioner-scoped/consent-aware workflows instead.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.hospital import Appointment, Hospital, HospitalStaff, Visit
from app.models.user import User


client = TestClient(app)


def auth(email: str) -> dict:
    token = create_access_token(subject=email, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def create_user(db, *, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass"),
        full_name=f"P0 {role}",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_hospital(db, name: str) -> Hospital:
    hospital = Hospital(name=name, is_active=True)
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


def add_membership(db, *, user_id: int, hospital_id: int) -> None:
    db.add(
        HospitalStaff(
            user_id=user_id,
            hospital_id=hospital_id,
            role="doctor",
            is_active=True,
        )
    )
    db.commit()


def create_visit(db, *, patient_id: int, doctor_id: int, hospital_id: int) -> Visit:
    visit = Visit(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        date=datetime.now(timezone.utc),
        reason="P0 private visit",
        status="completed",
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def create_appointment(db, *, patient_id: int, doctor_id: int, hospital_id: int) -> Appointment:
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        scheduled_time=datetime.now(timezone.utc) + timedelta(days=1),
        reason="P0 private appointment",
        notes="confidential",
        status="scheduled",
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def test_patient_cannot_list_another_patients_visits(db_session):
    hospital = create_hospital(db_session, "P0 Visit Hospital")
    patient_a = create_user(db_session, email="p0_visit_patient_a@test.com", role="patient")
    patient_b = create_user(db_session, email="p0_visit_patient_b@test.com", role="patient")
    doctor = create_user(db_session, email="p0_visit_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    create_visit(
        db_session,
        patient_id=patient_b.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.get(
        f"/api/visits/patient/{patient_b.id}",
        headers=auth(patient_a.email),
    )

    assert response.status_code == 403


def test_practitioner_cannot_use_patient_visit_history_endpoint(db_session):
    hospital = create_hospital(db_session, "P0 Visit Practitioner Hospital")
    patient = create_user(db_session, email="p0_visit_target@test.com", role="patient")
    doctor = create_user(db_session, email="p0_visit_attacker@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    create_visit(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.get(
        f"/api/visits/patient/{patient.id}",
        headers=auth(doctor.email),
    )

    assert response.status_code == 403


def test_patient_cannot_list_another_patients_appointments(db_session):
    hospital = create_hospital(db_session, "P0 Appointment Hospital")
    patient_a = create_user(db_session, email="p0_appt_patient_a@test.com", role="patient")
    patient_b = create_user(db_session, email="p0_appt_patient_b@test.com", role="patient")
    doctor = create_user(db_session, email="p0_appt_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    create_appointment(
        db_session,
        patient_id=patient_b.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.get(
        f"/api/appointments/patient/{patient_b.id}",
        headers=auth(patient_a.email),
    )

    assert response.status_code == 403


def test_practitioner_cannot_use_patient_appointment_history_endpoint(db_session):
    hospital = create_hospital(db_session, "P0 Appointment Practitioner Hospital")
    patient = create_user(db_session, email="p0_appt_target@test.com", role="patient")
    doctor = create_user(db_session, email="p0_appt_attacker@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.get(
        f"/api/appointments/patient/{patient.id}",
        headers=auth(doctor.email),
    )

    assert response.status_code == 403


def test_patient_can_still_list_own_appointments(db_session):
    hospital = create_hospital(db_session, "P0 Appointment Own Hospital")
    patient = create_user(db_session, email="p0_appt_owner@test.com", role="patient")
    doctor = create_user(db_session, email="p0_appt_owner_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    appointment = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.get(
        f"/api/appointments/patient/{patient.id}",
        headers=auth(patient.email),
    )

    assert response.status_code == 200
    returned_ids = {item["id"] for item in response.json()}
    assert appointment.id in returned_ids
