"""Regression coverage for the high-severity P1 remediation set."""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.audit import AuditLog
from app.models.hospital import Appointment, Hospital, HospitalStaff, Visit
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    DenialReason,
    Operation,
    ResourceType,
)

client = TestClient(app)


def auth(email: str) -> dict:
    token = create_access_token(subject=email, expires_delta=timedelta(minutes=30))
    return {"Authorization": f"Bearer {token}"}


def create_user(db: Session, *, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("testpass"),
        full_name=f"P1 {role}",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_hospital(db: Session, name: str) -> Hospital:
    hospital = Hospital(name=name, is_active=True)
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


def add_membership(db: Session, *, user_id: int, hospital_id: int) -> HospitalStaff:
    membership = HospitalStaff(
        user_id=user_id,
        hospital_id=hospital_id,
        role="doctor",
        is_active=True,
    )
    db.add(membership)
    db.commit()
    db.refresh(membership)
    return membership


def create_visit(
    db: Session,
    *,
    patient_id: int,
    doctor_id: int,
    hospital_id: int,
) -> Visit:
    visit = Visit(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        date=datetime.now(timezone.utc),
        reason="P1 assigned visit",
        status="completed",
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


def create_appointment(
    db: Session,
    *,
    patient_id: int,
    doctor_id: int,
    hospital_id: int,
    status: str = "scheduled",
) -> Appointment:
    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hospital_id,
        scheduled_time=datetime.now(timezone.utc) + timedelta(days=1),
        reason="P1 appointment",
        notes="initial note",
        status=status,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def test_visit_create_succeeds_for_assigned_member_practitioner(db_session: Session):
    hospital = create_hospital(db_session, "P1 Visit Create Hospital")
    patient = create_user(db_session, email="p1_visit_patient@test.com", role="patient")
    doctor = create_user(db_session, email="p1_visit_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)

    visit_date = datetime.now(timezone.utc).isoformat()
    response = client.post(
        "/api/visits",
        headers=auth(doctor.email),
        json={
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "hospital_id": hospital.id,
            "visit_date": visit_date,
            "reason": "Follow-up",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["patient_id"] == patient.id
    assert body["doctor_id"] == doctor.id
    assert body["hospital_id"] == hospital.id
    assert body["visit_date"] is not None


def test_visit_create_rejects_practitioner_identity_spoof(db_session: Session):
    hospital = create_hospital(db_session, "P1 Visit Spoof Hospital")
    patient = create_user(db_session, email="p1_visit_spoof_patient@test.com", role="patient")
    doctor_a = create_user(db_session, email="p1_visit_doctor_a@test.com", role="doctor")
    doctor_b = create_user(db_session, email="p1_visit_doctor_b@test.com", role="doctor")
    add_membership(db_session, user_id=doctor_a.id, hospital_id=hospital.id)

    response = client.post(
        "/api/visits",
        headers=auth(doctor_a.email),
        json={
            "patient_id": patient.id,
            "doctor_id": doctor_b.id,
            "hospital_id": hospital.id,
            "visit_date": datetime.now(timezone.utc).isoformat(),
            "reason": "Spoof attempt",
        },
    )

    assert response.status_code == 403


def test_visit_create_rejects_non_member_practitioner(db_session: Session):
    hospital = create_hospital(db_session, "P1 Visit Membership Hospital")
    patient = create_user(db_session, email="p1_visit_member_patient@test.com", role="patient")
    doctor = create_user(db_session, email="p1_visit_nonmember@test.com", role="doctor")

    response = client.post(
        "/api/visits",
        headers=auth(doctor.email),
        json={
            "patient_id": patient.id,
            "doctor_id": doctor.id,
            "hospital_id": hospital.id,
            "visit_date": datetime.now(timezone.utc).isoformat(),
            "reason": "No membership",
        },
    )

    assert response.status_code == 403


def test_document_create_cae_requires_assigned_visit(db_session: Session):
    hospital = create_hospital(db_session, "P1 Document CAE Hospital")
    patient = create_user(db_session, email="p1_document_patient@test.com", role="patient")
    assigned = create_user(db_session, email="p1_document_assigned@test.com", role="doctor")
    other = create_user(db_session, email="p1_document_other@test.com", role="doctor")
    add_membership(db_session, user_id=assigned.id, hospital_id=hospital.id)
    add_membership(db_session, user_id=other.id, hospital_id=hospital.id)
    visit = create_visit(
        db_session,
        patient_id=patient.id,
        doctor_id=assigned.id,
        hospital_id=hospital.id,
    )

    decision = AuthorizationService(db_session).authorize(
        AuthorizationContext(
            actor=other,
            operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db_session,
            resource=visit,
            patient_id=patient.id,
            hospital_id=hospital.id,
            requires_consent=False,
        )
    )

    assert decision.allowed is False
    assert decision.reason == DenialReason.RELATIONSHIP_REQUIRED


def test_document_upload_rejects_other_doctors_visit_before_storage(db_session: Session):
    hospital = create_hospital(db_session, "P1 Document Upload Hospital")
    patient = create_user(db_session, email="p1_upload_patient@test.com", role="patient")
    assigned = create_user(db_session, email="p1_upload_assigned@test.com", role="doctor")
    other = create_user(db_session, email="p1_upload_other@test.com", role="doctor")
    add_membership(db_session, user_id=assigned.id, hospital_id=hospital.id)
    add_membership(db_session, user_id=other.id, hospital_id=hospital.id)
    visit = create_visit(
        db_session,
        patient_id=patient.id,
        doctor_id=assigned.id,
        hospital_id=hospital.id,
    )

    response = client.post(
        "/api/documents",
        headers=auth(other.email),
        data={
            "visit_id": str(visit.id),
            "document_type": "prescription",
            "title": "Should be blocked",
        },
        files={"file": ("blocked.txt", b"blocked", "text/plain")},
    )

    assert response.status_code == 403
    assert "assigned" in response.json()["detail"].lower()


def test_doctor_cannot_update_another_doctors_appointment(db_session: Session):
    hospital = create_hospital(db_session, "P1 Appointment Ownership Hospital")
    patient = create_user(db_session, email="p1_appt_owner_patient@test.com", role="patient")
    doctor_a = create_user(db_session, email="p1_appt_owner_a@test.com", role="doctor")
    doctor_b = create_user(db_session, email="p1_appt_owner_b@test.com", role="doctor")
    add_membership(db_session, user_id=doctor_a.id, hospital_id=hospital.id)
    add_membership(db_session, user_id=doctor_b.id, hospital_id=hospital.id)
    appointment = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor_a.id,
        hospital_id=hospital.id,
    )

    response = client.patch(
        f"/api/appointments/{appointment.id}",
        headers=auth(doctor_b.email),
        json={"status": "confirmed"},
    )

    assert response.status_code == 403


def test_patient_can_cancel_but_cannot_complete_appointment(db_session: Session):
    hospital = create_hospital(db_session, "P1 Appointment State Hospital")
    patient = create_user(db_session, email="p1_state_patient@test.com", role="patient")
    doctor = create_user(db_session, email="p1_state_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)

    cancellable = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )
    cancelled = client.patch(
        f"/api/appointments/{cancellable.id}",
        headers=auth(patient.email),
        json={"status": "cancelled"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    second = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )
    completed = client.patch(
        f"/api/appointments/{second.id}",
        headers=auth(patient.email),
        json={"status": "completed"},
    )
    assert completed.status_code == 409


def test_invalid_appointment_status_is_schema_rejected(db_session: Session):
    hospital = create_hospital(db_session, "P1 Appointment Enum Hospital")
    patient = create_user(db_session, email="p1_enum_patient@test.com", role="patient")
    doctor = create_user(db_session, email="p1_enum_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    appointment = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.patch(
        f"/api/appointments/{appointment.id}",
        headers=auth(patient.email),
        json={"status": "totally_invalid"},
    )

    assert response.status_code == 422


def test_patient_cannot_modify_practitioner_notes(db_session: Session):
    hospital = create_hospital(db_session, "P1 Appointment Notes Hospital")
    patient = create_user(db_session, email="p1_notes_patient@test.com", role="patient")
    doctor = create_user(db_session, email="p1_notes_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    appointment = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    response = client.patch(
        f"/api/appointments/{appointment.id}",
        headers=auth(patient.email),
        json={"notes": "patient overwrite"},
    )

    assert response.status_code == 403


def test_assigned_doctor_can_follow_valid_status_state_machine(db_session: Session):
    hospital = create_hospital(db_session, "P1 Doctor State Hospital")
    patient = create_user(db_session, email="p1_doc_state_patient@test.com", role="patient")
    doctor = create_user(db_session, email="p1_doc_state_doctor@test.com", role="doctor")
    add_membership(db_session, user_id=doctor.id, hospital_id=hospital.id)
    appointment = create_appointment(
        db_session,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
    )

    confirmed = client.patch(
        f"/api/appointments/{appointment.id}",
        headers=auth(doctor.email),
        json={"status": "confirmed", "notes": "confirmed by doctor"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"

    completed = client.patch(
        f"/api/appointments/{appointment.id}",
        headers=auth(doctor.email),
        json={"status": "completed"},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "completed"


def test_successful_phi_list_is_audited(db_session: Session):
    patient = create_user(db_session, email="p1_list_audit_patient@test.com", role="patient")

    response = client.get("/api/appointments/patient", headers=auth(patient.email))
    assert response.status_code == 200, response.text

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.actor_id == patient.id,
            AuditLog.patient_id == patient.id,
            AuditLog.operation == Operation.LIST.value,
            AuditLog.resource_type == ResourceType.APPOINTMENT.value,
            AuditLog.decision == "ALLOW",
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.metadata_json is not None
    assert '"list_access": true' in audit.metadata_json
