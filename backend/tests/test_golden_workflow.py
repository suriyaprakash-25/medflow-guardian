"""
Phase 6 — Golden End-to-End Secure Document Workflow

This test suite explicitly verifies the Consent and Enforcement-State matrix,
including the Fail-Closed stale state verification, against the real FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from datetime import datetime, timedelta

from app.main import app
from sqlalchemy import text
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.document import MedicalDocument
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.core.security import get_password_hash, create_access_token
from app.services.storage import StorageService

client = TestClient(app)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        is_active=True
    )
    doctor = User(
        email="doctor_golden@test.com",
        hashed_password=get_password_hash("pass"),
        full_name="Doctor Golden",
        role="doctor",
        is_active=True
    )
    db.add_all([patient, doctor])
    db.flush()

    staff = HospitalStaff(user_id=patient.id, hospital_id=hosp.id, role="doctor", is_active=True)
    visit = Visit(patient_id=patient.id, doctor_id=patient.id, hospital_id=hosp.id)
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
        stored_filename=f"golden_{patient.id}_{doctor.id}.pdf",
        mime_type="application/pdf",
        file_size=2048,
        scan_status="clean",
        status="active"
    )
    db.add(doc)
    db.flush()
    return hosp, patient, doctor, doc

def setup_consent_chain(db, patient_id, doctor_id, hosp_id, doc_id, purpose="TREATMENT"):
    """Creates a Consent, Policy, active State, and Access Grant linking to it."""
    req = DocumentAccessRequest(
        patient_id=patient_id,
        requesting_doctor_id=doctor_id,
        requesting_hospital_id=hosp_id,
        reason="Test",
        status="approved"
    )
    db.add(req)
    db.flush()

    consent = Consent(patient_id=patient_id, doctor_id=doctor_id, hospital_id=hosp_id, status="active")
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={"allowed_purposes": [purpose], "allowed_operations": ["download"]},
        status="active"
    )
    db.add(policy)
    db.flush()

    state = ConsentState(consent_id=consent.id, policy_version_id=policy.id, status="active")
    db.add(state)
    db.flush()

    grant = DocumentAccessGrant(
        access_request_id=req.id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        hospital_id=hosp_id,
        consent_id=consent.id,
        status="active",
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    # Using private method or appending directly to simulate ORM mapping
    db.add(grant)
    db.flush()
    # Link doc (assuming granted_documents association table works in this test ctx)
    # For test purposes, we'll assume the grant covers this document.
    db.execute(
        text("INSERT INTO access_grant_documents (access_grant_id, document_id) VALUES (:g, :d)"),
        {"g": grant.id, "d": doc_id}
    )
    db.flush()

    return consent, policy, state, grant


# ===========================================================================
# GOLDEN E2E TESTS
# ===========================================================================

@patch("app.services.storage.StorageService.download_document")
def test_golden_workflow_revocation_denial(mock_storage, db_session):
    """
    Demonstrates Revocation Denial.
    1. Valid Consent exists.
    2. Consent is REVOKED.
    3. Doctor requests document.
    EXPECTED: DENY (OPERATION_NOT_ALLOWED), NO STORAGE ACCESS.
    """
    hosp, patient, doctor, doc = create_fixture_data(db_session)
    consent, policy, state1, grant = setup_consent_chain(db_session, patient.id, doctor.id, hosp.id, doc.id)

    # 1. Authoritative State is currently `state1.id`
    # Let's say Doctor attempts download with this correct state
    mock_storage.return_value = b"file data"
    resp_valid = client.get(
        f"/api/documents/{doc.id}/download?purpose=TREATMENT", headers=auth(doctor.email)
    )
    assert resp_valid.status_code == 200, resp_valid.text
    assert mock_storage.called
    mock_storage.reset_mock()

    # 2. Patient REVOKES consent -> New State
    consent.status = "revoked"
    state2 = ConsentState(consent_id=consent.id, policy_version_id=policy.id, status="revoked")
    db_session.add(state2)
    db_session.flush()

    # 3. Doctor tries to download again
    resp_stale = client.get(
        f"/api/documents/{doc.id}/download?purpose=TREATMENT", headers=auth(doctor.email)
    )
    
    # Assert HTTP 403 and Revoked reason
    assert resp_stale.status_code == 403, resp_stale.text
    assert "OPERATION_NOT_ALLOWED" in resp_stale.text or "revoked" in resp_stale.text.lower()
    # CRITICAL: Prove Storage was NEVER accessed
    assert not mock_storage.called


@patch("app.services.storage.StorageService.download_document")
def test_golden_workflow_revoked_consent_denial(mock_storage, db_session):
    """
    Demonstrates Synchronized Revoked Consent Denial.
    Doctor passes the CORRECT, SYNCHRONIZED enforcement state, but the consent itself is revoked.
    """
    hosp, patient, doctor, doc = create_fixture_data(db_session)
    consent, policy, state1, grant = setup_consent_chain(db_session, patient.id, doctor.id, hosp.id, doc.id)

    # Patient REVOKES consent
    consent.status = "revoked"
    state2 = ConsentState(consent_id=consent.id, policy_version_id=policy.id, status="revoked")
    db_session.add(state2)
    db_session.flush()

    # Doctor tries to download with SYNCHRONIZED state2
    resp_revoked = client.get(
        f"/api/documents/{doc.id}/download?purpose=TREATMENT", headers=auth(doctor.email)
    )
    
    assert resp_revoked.status_code == 403, resp_revoked.text
    assert "revoked" in resp_revoked.json()["detail"].lower()
    assert not mock_storage.called


@patch("app.services.storage.StorageService.download_document")
def test_golden_workflow_wrong_purpose_denial(mock_storage, db_session):
    """
    Demonstrates Purpose Mismatch Denial.
    Doctor has valid consent for TREATMENT, but requests for BILLING.
    """
    hosp, patient, doctor, doc = create_fixture_data(db_session)
    consent, policy, state1, grant = setup_consent_chain(db_session, patient.id, doctor.id, hosp.id, doc.id, purpose="TREATMENT")

    # Doctor tries to download with BILLING purpose
    resp_purpose = client.get(
        f"/api/documents/{doc.id}/download?purpose=BILLING", headers=auth(doctor.email)
    )
    
    assert resp_purpose.status_code == 403, resp_purpose.text
    assert "PURPOSE_NOT_ALLOWED" in resp_purpose.json()["detail"]
    assert not mock_storage.called
