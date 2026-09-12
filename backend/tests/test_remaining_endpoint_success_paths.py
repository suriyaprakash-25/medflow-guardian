"""Database-backed success-path coverage for the previously uncovered API routes."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.clinical import Medication
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.notification import Notification
from app.models.user import User


client = TestClient(app)


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=user.email)}"}


def _user(db, *, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass"),
        full_name=f"Endpoint {role}",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _hospital(db, name: str = "Endpoint Hospital") -> Hospital:
    hospital = Hospital(name=name, is_active=True)
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


def _membership(db, *, user: User, hospital: Hospital, role: str = "doctor"):
    membership = HospitalStaff(
        user_id=user.id,
        hospital_id=hospital.id,
        role=role,
        is_active=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def _visit(db, *, patient: User, doctor: User, hospital: Hospital) -> Visit:
    visit = Visit(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        date=datetime.now(timezone.utc),
        status="completed",
        reason="Endpoint certification",
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def _active_consent(db, *, patient: User, doctor: User, hospital: Hospital):
    consent = Consent(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        status="active",
    )
    db.add(consent)
    db.flush()
    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": ["create", "read", "list", "download"],
        },
        status="active",
    )
    db.add(policy)
    db.flush()
    db.add(
        ConsentState(
            consent_id=consent.id,
            policy_version_id=policy.id,
            status="active",
        )
    )
    db.commit()
    return consent


def test_patient_monitoring_profile_appointment_and_visit_routes(db_session):
    hospital = _hospital(db_session)
    patient = _user(db_session, email="endpoint-patient@example.com", role="patient")
    doctor = _user(db_session, email="endpoint-doctor@example.com", role="doctor")
    _membership(db_session, user=doctor, hospital=hospital)
    _visit(db_session, patient=patient, doctor=doctor, hospital=hospital)
    notification = Notification(
        user_id=patient.id,
        type="endpoint-test",
        message="Endpoint validation notification",
        is_read=False,
    )
    db_session.add(notification)
    db_session.commit()

    patient_headers = _auth(patient)
    doctor_headers = _auth(doctor)

    assert client.get("/api/users/patient-profile", headers=patient_headers).status_code == 200
    profile = client.post(
        "/api/users/patient-profile",
        headers=patient_headers,
        json={"blood_type": "O+", "allergies": "none"},
    )
    assert profile.status_code == 200, profile.text

    reading = client.post(
        "/api/readings",
        headers=patient_headers,
        json={
            "heart_rate": 72,
            "oxygen_level": 98,
            "blood_pressure_sys": 120,
            "blood_pressure_dia": 80,
            "is_simulated": True,
        },
    )
    assert reading.status_code == 200, reading.text
    assert client.get("/api/readings/patient", headers=patient_headers).status_code == 200
    assert client.get(f"/api/readings/{patient.id}", headers=doctor_headers).status_code == 200

    sent = client.post(
        "/api/messages",
        headers=patient_headers,
        json={"receiver_id": doctor.id, "content": "Endpoint validation"},
    )
    assert sent.status_code == 200, sent.text
    history = client.get(f"/api/messages/{patient.id}", headers=doctor_headers)
    assert history.status_code == 200, history.text

    assert client.post("/api/notifications/read-all", headers=patient_headers).status_code == 200
    assert client.get(f"/api/hospitals/{hospital.id}", headers=patient_headers).status_code == 200
    assert client.get("/api/visits/patient", headers=patient_headers).status_code == 200
    assert client.get("/api/visits/doctor", headers=doctor_headers).status_code == 200

    appointment = client.post(
        "/api/appointments",
        headers=patient_headers,
        json={
            "hospital_id": hospital.id,
            "doctor_id": doctor.id,
            "scheduled_time": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "reason": "Endpoint certification",
        },
    )
    assert appointment.status_code == 200, appointment.text
    doctor_appointments = client.get(
        f"/api/appointments/doctor/{doctor.id}", headers=doctor_headers
    )
    assert doctor_appointments.status_code == 200, doctor_appointments.text


def test_clinical_success_routes(db_session):
    hospital = _hospital(db_session, "Clinical Endpoint Hospital")
    patient = _user(db_session, email="clinical-patient@example.com", role="patient")
    doctor = _user(db_session, email="clinical-doctor@example.com", role="doctor")
    _membership(db_session, user=doctor, hospital=hospital)
    _visit(db_session, patient=patient, doctor=doctor, hospital=hospital)
    _active_consent(db_session, patient=patient, doctor=doctor, hospital=hospital)
    medication = Medication(name="Endpoint Medicine", description="test")
    db_session.add(medication)
    db_session.commit()
    db_session.refresh(medication)

    headers = _auth(doctor)
    query = f"?purpose=TREATMENT&hospital_id={hospital.id}"
    prescription = client.post(
        "/api/clinical/prescriptions?purpose=TREATMENT",
        headers=headers,
        json={
            "patient_id": patient.id,
            "medication_id": medication.id,
            "hospital_id": hospital.id,
            "dosage": "10 mg",
            "frequency": "daily",
            "start_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert prescription.status_code == 200, prescription.text
    lab = client.post(
        "/api/clinical/labs?purpose=TREATMENT",
        headers=headers,
        json={
            "patient_id": patient.id,
            "hospital_id": hospital.id,
            "test_name": "CBC",
            "result_value": "normal",
            "test_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert lab.status_code == 200, lab.text
    note = client.post(
        "/api/clinical/notes?purpose=TREATMENT",
        headers=headers,
        json={
            "patient_id": patient.id,
            "hospital_id": hospital.id,
            "title": "Endpoint note",
            "content": "Validated",
            "note_type": "general",
        },
    )
    assert note.status_code == 200, note.text

    assert client.get(
        f"/api/clinical/labs/patient/{patient.id}{query}", headers=headers
    ).status_code == 200
    assert client.get(
        f"/api/clinical/notes/patient/{patient.id}{query}", headers=headers
    ).status_code == 200


def test_access_request_grant_reject_and_revoke_routes(db_session):
    hospital = _hospital(db_session, "Access Endpoint Hospital")
    patient = _user(db_session, email="access-patient@example.com", role="patient")
    doctor = _user(db_session, email="access-doctor@example.com", role="doctor")
    _membership(db_session, user=doctor, hospital=hospital)
    _visit(db_session, patient=patient, doctor=doctor, hospital=hospital)
    patient_headers = _auth(patient)
    doctor_headers = _auth(doctor)

    def create_request():
        response = client.post(
            "/api/access-requests",
            headers=doctor_headers,
            json={
                "patient_id": patient.id,
                "hospital_id": hospital.id,
                "document_ids": [],
                "reason": "Endpoint certification",
            },
        )
        assert response.status_code == 200, response.text
        return response.json()["id"]

    rejected_id = create_request()
    assert client.get("/api/access-requests/patient", headers=patient_headers).status_code == 200
    rejected = client.post(
        f"/api/access-requests/{rejected_id}/reject",
        headers=patient_headers,
        json={"rejection_reason": "Endpoint validation"},
    )
    assert rejected.status_code == 200, rejected.text

    approved_id = create_request()
    approved = client.post(
        f"/api/access-requests/{approved_id}/approve",
        headers=patient_headers,
        json={"duration_hours": 1, "document_ids": []},
    )
    assert approved.status_code == 200, approved.text
    grant_id = approved.json()["id"]
    assert client.get("/api/access-grants/patient", headers=patient_headers).status_code == 200
    assert client.get("/api/access-grants/doctor", headers=doctor_headers).status_code == 200
    revoked = client.post(
        f"/api/access-grants/{grant_id}/revoke", headers=patient_headers
    )
    assert revoked.status_code == 200, revoked.text


def test_admin_update_list_and_deactivate_routes(db_session):
    admin = _user(db_session, email="platform-admin@example.com", role="platform_admin")
    hospital = _hospital(db_session, "Admin Endpoint Hospital")
    headers = _auth(admin)

    updated = client.put(
        f"/api/admin/organization/{hospital.id}",
        headers=headers,
        json={"address": "Validated address"},
    )
    assert updated.status_code == 200, updated.text

    provisioned = client.post(
        f"/api/admin/staff?hospital_id={hospital.id}",
        headers=headers,
        json={
            "email": "managed-staff@example.com",
            "full_name": "Managed Staff",
            "password": "strong-password-123",
            "role": "doctor",
        },
    )
    assert provisioned.status_code == 200, provisioned.text
    membership_id = provisioned.json()["membership_id"]
    assert client.get(
        f"/api/admin/staff?hospital_id={hospital.id}", headers=headers
    ).status_code == 200
    changed = client.put(
        f"/api/admin/staff/{membership_id}?hospital_id={hospital.id}",
        headers=headers,
        json={"role": "staff"},
    )
    assert changed.status_code == 200, changed.text
    removed = client.delete(
        f"/api/admin/staff/{membership_id}?hospital_id={hospital.id}", headers=headers
    )
    assert removed.status_code == 200, removed.text


def test_auth_profile_password_and_readiness_routes(db_session):
    user = _user(db_session, email="auth-endpoint@example.com", role="patient")
    headers = _auth(user)
    updated = client.patch(
        "/api/auth/me", headers=headers, json={"full_name": "Updated Endpoint User"}
    )
    assert updated.status_code == 200, updated.text
    changed = client.post(
        "/api/auth/change-password",
        headers=headers,
        json={"old_password": "testpass", "new_password": "new-test-password-123"},
    )
    assert changed.status_code == 200, changed.text
    ready = client.get("/ready")
    assert ready.status_code == 200, ready.text
    assert ready.json() == {"status": "ready"}
