from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.auth import Session as AuthSession
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.hospital import Hospital
from app.models.privacy import PrivacyLegalHold, PrivacyRequest
from app.models.user import PatientProfile, User


client = TestClient(app)


def _user(db, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password=get_password_hash("privacy-test-password"),
        full_name="Privacy Test User",
        phone_number="+15555550100",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(subject=user.email)}"}


def _consent_and_grant(db, patient: User, doctor: User, hospital: Hospital):
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
        status="active",
        policy_payload={"allowed_purposes": ["TREATMENT"], "allowed_operations": ["read"]},
    )
    db.add(policy)
    db.flush()
    db.add(ConsentState(consent_id=consent.id, policy_version_id=policy.id, status="active"))
    access_request = DocumentAccessRequest(
        patient_id=patient.id,
        requesting_doctor_id=doctor.id,
        requesting_hospital_id=hospital.id,
        reason="Privacy workflow",
        status="approved",
    )
    db.add(access_request)
    db.flush()
    grant = DocumentAccessGrant(
        access_request_id=access_request.id,
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id,
        consent_id=consent.id,
        status="active",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(grant)
    db.flush()
    return consent, grant


def test_consent_withdrawal_immediately_revokes_linked_grants(db_session):
    patient = _user(db_session, "withdrawal-patient@example.com", "patient")
    doctor = _user(db_session, "withdrawal-doctor@example.com", "doctor")
    hospital = Hospital(name="Withdrawal Hospital", is_active=True)
    db_session.add(hospital)
    db_session.flush()
    consent, grant = _consent_and_grant(db_session, patient, doctor, hospital)

    response = client.post(
        f"/api/consents/{consent.id}/transition",
        json={"target_status": "revoked", "reason": "Patient withdrew consent"},
        headers=_headers(patient),
    )
    assert response.status_code == 200, response.text
    db_session.refresh(grant)
    assert grant.status == "revoked"
    assert grant.revoked_at is not None


def test_deletion_request_is_blocked_by_hold_then_pseudonymizes_and_revokes(db_session):
    patient = _user(db_session, "deletion-patient@example.com", "patient")
    doctor = _user(db_session, "deletion-doctor@example.com", "doctor")
    admin = _user(db_session, "privacy-admin@example.com", "platform_admin")
    hospital = Hospital(name="Privacy Hospital", is_active=True)
    db_session.add(hospital)
    db_session.flush()
    consent, grant = _consent_and_grant(db_session, patient, doctor, hospital)
    profile = PatientProfile(
        user_id=patient.id,
        date_of_birth="1990-01-01",
        address="Sensitive address",
        emergency_contact_name="Sensitive contact",
        emergency_contact_phone="+15555550101",
    )
    session = AuthSession(
        user_id=patient.id,
        refresh_token_hash="privacy-refresh-hash",
        token_family="privacy-family",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db_session.add_all([profile, session])
    db_session.commit()

    created = client.post(
        "/api/privacy/requests",
        json={"request_type": "deletion", "reason": "Please delete my account"},
        headers=_headers(patient),
    )
    assert created.status_code == 201, created.text
    request_id = created.json()["id"]
    decision = client.post(
        f"/api/admin/privacy/requests/{request_id}/decision",
        json={"decision": "approved", "review_notes": "Identity verified"},
        headers=_headers(admin),
    )
    assert decision.status_code == 200, decision.text

    hold = client.post(
        "/api/admin/privacy/legal-holds",
        json={"patient_id": patient.id, "reason": "Open safety investigation"},
        headers=_headers(admin),
    )
    assert hold.status_code == 201, hold.text
    blocked = client.post(
        f"/api/admin/privacy/requests/{request_id}/execute",
        headers=_headers(admin),
    )
    assert blocked.status_code == 409

    released = client.post(
        f"/api/admin/privacy/legal-holds/{hold.json()['id']}/release",
        headers=_headers(admin),
    )
    assert released.status_code == 200, released.text
    executed = client.post(
        f"/api/admin/privacy/requests/{request_id}/execute",
        headers=_headers(admin),
    )
    assert executed.status_code == 200, executed.text
    assert executed.json()["status"] == "completed"

    db_session.refresh(patient)
    db_session.refresh(profile)
    db_session.refresh(session)
    db_session.refresh(consent)
    db_session.refresh(grant)
    assert patient.is_active is False
    assert patient.email == f"deleted+{patient.id}@invalid.medflow"
    assert patient.phone_number is None
    assert profile.address is None
    assert profile.date_of_birth is None
    assert session.revoked_at is not None
    assert consent.status == "revoked"
    assert grant.status == "revoked"
    assert db_session.query(PrivacyRequest).filter_by(id=request_id, status="completed").one()
    assert not db_session.query(PrivacyLegalHold).filter_by(patient_id=patient.id, active=True).first()


def test_non_patient_cannot_create_privacy_request(db_session):
    doctor = _user(db_session, "privacy-denied-doctor@example.com", "doctor")
    db_session.commit()
    response = client.post(
        "/api/privacy/requests",
        json={"request_type": "export"},
        headers=_headers(doctor),
    )
    assert response.status_code == 403
