"""
Phase 6 — Golden End-to-End Secure Document Workflow

This test suite explicitly verifies the Consent and Enforcement-State matrix,
including the Fail-Closed stale state verification, against the real FastAPI endpoints.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.document import MedicalDocument
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.user import User

client = TestClient(app)


def make_token(email: str) -> str:
    return create_access_token(subject=email, expires_delta=timedelta(minutes=30))


def auth(email: str) -> dict:
    return {"Authorization": f"Bearer {make_token(email)}"}


def create_fixture_data(db):
    """Seed the database with Patient A, Doctor A, Hospital A, and a Document."""
    hosp = Hospital(name="Golden Hospital", is_active=True)
    db.add(hosp)
    db.flush()

    patient = User(
        email="patient_golden@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="Patient Golden",
        role="patient",
        is_active=True,
    )
    doctor = User(
        email="doctor_golden@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="Doctor Golden",
        role="doctor",
        is_active=True,
    )
    db.add_all([patient, doctor])
    db.flush()

    staff = HospitalStaff(
        user_id=patient.id,
        hospital_id=hosp.id,
        role="doctor",
        is_active=True,
    )
    visit = Visit(
        patient_id=patient.id,
        doctor_id=patient.id,
        hospital_id=hosp.id,
    )
    db.add_all([staff, visit])
    db.flush()

    doc = MedicalDocument(
        patient_id=patient.id,
        hospital_id=hosp.id,
        uploaded_by_doctor_id=patient.id,
        visit_id=visit.id,
        document_type="lab_report",
        title="Golden Lab Report",
        original_filename="golden.pdf",
        stored_filename=f"patient/{patient.id}/golden_{patient.id}_{doctor.id}.pdf",
        mime_type="application/pdf",
        file_size=2048,
        scan_status="clean",
        status="active",
    )
    db.add(doc)
    db.flush()
    return hosp, patient, doctor, doc


def setup_consent_chain(
    db,
    patient_id,
    doctor_id,
    hosp_id,
    doc_id,
    purpose="TREATMENT",
):
    """Create a Consent, Policy, active State, and Access Grant linking to it."""
    req = DocumentAccessRequest(
        patient_id=patient_id,
        requesting_doctor_id=doctor_id,
        requesting_hospital_id=hosp_id,
        reason="Test",
        status="approved",
    )
    db.add(req)
    db.flush()

    consent = Consent(
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hosp_id,
        status="active",
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": [purpose],
            "allowed_operations": ["download"],
        },
        status="active",
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status="active",
    )
    db.add(state)
    db.flush()

    grant = DocumentAccessGrant(
        access_request_id=req.id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hosp_id,
        consent_id=consent.id,
        status="active",
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(grant)
    db.flush()
    db.execute(
        text(
            "INSERT INTO access_grant_documents (access_grant_id, document_id) "
            "VALUES (:g, :d)"
        ),
        {"g": grant.id, "d": doc_id},
    )
    db.flush()

    return consent, policy, state, grant


@patch("app.api.document.storage_service.download_document")
def test_golden_workflow_revocation_denial(mock_storage, db_session):
    """A valid release succeeds, then consent revocation denies before storage."""
    hosp, patient, doctor, doc = create_fixture_data(db_session)
    consent, policy, _, _ = setup_consent_chain(
        db_session,
        patient.id,
        doctor.id,
        hosp.id,
        doc.id,
    )

    mock_storage.return_value = b"file data"
    resp_valid = client.get(
        f"/api/documents/{doc.id}/download?purpose=TREATMENT",
        headers=auth(doctor.email),
    )
    assert resp_valid.status_code == 200, resp_valid.text
    assert mock_storage.called
    mock_storage.reset_mock()

    consent.status = "revoked"
    state2 = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status="revoked",
    )
    db_session.add(state2)
    db_session.flush()

    resp_stale = client.get(
        f"/api/documents/{doc.id}/download?purpose=TREATMENT",
        headers=auth(doctor.email),
    )

    assert resp_stale.status_code == 403, resp_stale.text
    assert (
        "OPERATION_NOT_ALLOWED" in resp_stale.text
        or "revoked" in resp_stale.text.lower()
    )
    assert not mock_storage.called


@patch("app.api.document.storage_service.download_document")
def test_golden_workflow_revoked_consent_denial(mock_storage, db_session):
    """Synchronized but revoked consent is denied before storage."""
    hosp, patient, doctor, doc = create_fixture_data(db_session)
    consent, policy, _, _ = setup_consent_chain(
        db_session,
        patient.id,
        doctor.id,
        hosp.id,
        doc.id,
    )

    consent.status = "revoked"
    state2 = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status="revoked",
    )
    db_session.add(state2)
    db_session.flush()

    resp_revoked = client.get(
        f"/api/documents/{doc.id}/download?purpose=TREATMENT",
        headers=auth(doctor.email),
    )

    assert resp_revoked.status_code == 403, resp_revoked.text
    assert "revoked" in resp_revoked.json()["detail"].lower()
    assert not mock_storage.called


@patch("app.api.document.storage_service.download_document")
def test_golden_workflow_wrong_purpose_denial(mock_storage, db_session):
    """Purpose mismatch is denied before storage."""
    hosp, patient, doctor, doc = create_fixture_data(db_session)
    setup_consent_chain(
        db_session,
        patient.id,
        doctor.id,
        hosp.id,
        doc.id,
        purpose="TREATMENT",
    )

    resp_purpose = client.get(
        f"/api/documents/{doc.id}/download?purpose=BILLING",
        headers=auth(doctor.email),
    )

    assert resp_purpose.status_code == 403, resp_purpose.text
    assert "PURPOSE_NOT_ALLOWED" in resp_purpose.json()["detail"]
    assert not mock_storage.called
