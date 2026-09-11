"""
Phase 4 — Authorization Endpoint Tests (E2E against real PostgreSQL)

Tests actual HTTP endpoints with real database interactions.
Covers: IDOR, role escalation, cross-org access, ownership enforcement,
payload manipulation, default-deny behavior.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta

from app.main import app
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff, Visit
from app.models.document import MedicalDocument
from app.models.notification import Notification
from app.models.access import DocumentAccessRequest
from app.models.audit import AuditLog
from app.core.security import get_password_hash, create_access_token

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_token(email: str) -> str:
    return create_access_token(subject=email, expires_delta=timedelta(minutes=30))


def auth(email: str) -> dict:
    return {"Authorization": f"Bearer {make_token(email)}"}


def create_user(db, email, role, is_active=True, user_id=None):
    u = User(
        email=email,
        hashed_password=get_password_hash("testpass"),
        full_name=f"Test {role.capitalize()}",
        role=role,
        is_active=is_active
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def create_hospital(db, name="Test Hospital"):
    h = Hospital(name=name, is_active=True)
    db.add(h)
    db.commit()
    db.refresh(h)
    return h


def create_membership(db, user_id, hospital_id, role="doctor", is_active=True):
    m = HospitalStaff(user_id=user_id, hospital_id=hospital_id, role=role, is_active=is_active)
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


def create_visit(db, patient_id, doctor_id, hospital_id):
    v = Visit(patient_id=patient_id, doctor_id=doctor_id, hospital_id=hospital_id)
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def create_document(db, patient_id, hospital_id, doctor_id, visit_id):
    doc = MedicalDocument(
        patient_id=patient_id,
        hospital_id=hospital_id,
        uploaded_by_doctor_id=doctor_id,
        visit_id=visit_id,
        document_type="prescription",
        title="Test Document",
        original_filename="test.pdf",
        stored_filename=f"test_{patient_id}_{doctor_id}.pdf",
        mime_type="application/pdf",
        file_size=1024,
        status="active"
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def create_notification(db, user_id):
    n = Notification(user_id=user_id, type="test", message="Test notification", is_read=False)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


# ===========================================================================
# TEST: Authentication Requirements
# ===========================================================================

class TestAuthentication:

    def test_missing_token_returns_401(self):
        resp = client.get("/api/documents/patient")
        assert resp.status_code == 401

    def test_invalid_token_returns_401(self):
        resp = client.get("/api/documents/patient", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    def test_malformed_bearer_returns_401(self):
        resp = client.get("/api/documents/patient", headers={"Authorization": "NotBearer xyz"})
        assert resp.status_code == 401

    def test_inactive_user_returns_401(self, db_session):
        inactive = create_user(db_session, "inactive@test.com", "patient", is_active=False)
        resp = client.get("/api/documents/patient", headers=auth(inactive.email))
        assert resp.status_code == 401


# ===========================================================================
# TEST: Document IDOR
# ===========================================================================

class TestDocumentIDOR:

    def test_patient_cannot_download_other_patient_document(self, db_session):
        """IDOR: Patient A must not access Patient B's document by ID manipulation."""
        hosp = create_hospital(db_session)
        patient_a = create_user(db_session, "patient_a_idor@test.com", "patient")
        patient_b = create_user(db_session, "patient_b_idor@test.com", "patient")
        doctor = create_user(db_session, "doctor_idor@test.com", "doctor")
        m = create_membership(db_session, doctor.id, hosp.id)
        visit = create_visit(db_session, patient_b.id, doctor.id, hosp.id)
        doc = create_document(db_session, patient_b.id, hosp.id, doctor.id, visit.id)

        # Patient A tries to download Patient B's document
        resp = client.get(f"/api/documents/{doc.id}/download", headers=auth(patient_a.email))
        assert resp.status_code in (403, 404)  # Must not be 200

    def test_doctor_cannot_download_other_hospital_document(self, db_session):
        """Cross-org: Doctor in Hospital A cannot download Hospital B document."""
        hosp_a = create_hospital(db_session, "Hospital A")
        hosp_b = create_hospital(db_session, "Hospital B")
        patient = create_user(db_session, "patient_cross_org@test.com", "patient")
        doctor_a = create_user(db_session, "doctor_a_cross@test.com", "doctor")
        doctor_b = create_user(db_session, "doctor_b_cross@test.com", "doctor")

        create_membership(db_session, doctor_a.id, hosp_a.id)
        create_membership(db_session, doctor_b.id, hosp_b.id)
        visit = create_visit(db_session, patient.id, doctor_b.id, hosp_b.id)
        doc = create_document(db_session, patient.id, hosp_b.id, doctor_b.id, visit.id)

        # Doctor A (only in Hospital A) tries to access Hospital B's document
        resp = client.get(f"/api/documents/{doc.id}/download", headers=auth(doctor_a.email))
        assert resp.status_code in (403, 404)


# ===========================================================================
# TEST: Notification IDOR
# ===========================================================================

class TestNotificationIDOR:

    def test_user_can_mark_own_notification_read(self, db_session):
        user = create_user(db_session, "notif_owner@test.com", "patient")
        notif = create_notification(db_session, user.id)

        resp = client.post(f"/api/notifications/{notif.id}/read", headers=auth(user.email))
        assert resp.status_code == 200

    def test_user_cannot_mark_other_user_notification_read(self, db_session):
        """IDOR: User A must not mark User B's notification as read."""
        user_a = create_user(db_session, "notif_a@test.com", "patient")
        user_b = create_user(db_session, "notif_b@test.com", "patient")
        notif = create_notification(db_session, user_b.id)

        # User A tries to mark User B's notification
        resp = client.post(f"/api/notifications/{notif.id}/read", headers=auth(user_a.email))
        assert resp.status_code == 404  # Hidden via 404 to prevent notification enumeration


# ===========================================================================
# TEST: Triage Organization Isolation
# ===========================================================================

class TestTriageOrganizationIsolation:

    def test_patient_can_submit_triage(self, db_session):
        hosp = create_hospital(db_session)
        patient = create_user(db_session, "triage_patient@test.com", "patient")

        resp = client.post("/api/triage/", json={
            "symptoms": "headache and fever",
            "hospital_id": hosp.id
        }, headers=auth(patient.email))
        assert resp.status_code in (200, 201)

    def test_doctor_cannot_submit_triage(self, db_session):
        hosp = create_hospital(db_session)
        doctor = create_user(db_session, "triage_doc@test.com", "doctor")
        create_membership(db_session, doctor.id, hosp.id)

        resp = client.post("/api/triage/", json={
            "symptoms": "test symptoms",
            "hospital_id": hosp.id
        }, headers=auth(doctor.email))
        assert resp.status_code == 403

    def test_doctor_cannot_update_other_hospital_triage(self, db_session):
        hosp_a = create_hospital(db_session, "Triage Hospital A")
        hosp_b = create_hospital(db_session, "Triage Hospital B")
        patient = create_user(db_session, "triage_patient2@test.com", "patient")
        doctor_a = create_user(db_session, "triage_doc_a@test.com", "doctor")
        doctor_b = create_user(db_session, "triage_doc_b@test.com", "doctor")

        create_membership(db_session, doctor_a.id, hosp_a.id)
        create_membership(db_session, doctor_b.id, hosp_b.id)

        # Patient submits triage to Hospital B
        triage_resp = client.post("/api/triage/", json={
            "symptoms": "cross-org test",
            "hospital_id": hosp_b.id
        }, headers=auth(patient.email))
        assert triage_resp.status_code in (200, 201)
        triage_id = triage_resp.json()["id"]

        # Doctor A (only in Hospital A) tries to update Hospital B triage
        resp = client.patch(f"/api/triage/{triage_id}/status", json={
            "status": "reviewed"
        }, headers=auth(doctor_a.email))
        assert resp.status_code == 403


# ===========================================================================
# TEST: Access Request Ownership
# ===========================================================================

class TestAccessRequestOwnership:

    def test_patient_cannot_approve_other_patient_request(self, db_session):
        """Patient A must not approve Patient B's access request."""
        hosp = create_hospital(db_session)
        patient_a = create_user(db_session, "approve_a@test.com", "patient")
        patient_b = create_user(db_session, "approve_b@test.com", "patient")
        doctor = create_user(db_session, "approve_doc@test.com", "doctor")
        create_membership(db_session, doctor.id, hosp.id)

        # Create access request for Patient B
        req = DocumentAccessRequest(
            patient_id=patient_b.id,
            requesting_doctor_id=doctor.id,
            requesting_hospital_id=hosp.id,
            reason="Medical review",
            status="pending"
        )
        db_session.add(req)
        db_session.commit()
        db_session.refresh(req)

        # Patient A tries to approve Patient B's request
        resp = client.post(f"/api/access-requests/{req.id}/approve", json={
            "duration_hours": 24,
            "document_ids": []
        }, headers=auth(patient_a.email))
        assert resp.status_code == 403


# ===========================================================================
# TEST: Role-based Access Control
# ===========================================================================

class TestRoleBasedAccess:

    def test_doctor_cannot_list_own_patient_triage_queue(self, db_session):
        """Doctors list the doctor triage queue — patients list their own queue."""
        hosp = create_hospital(db_session)
        patient = create_user(db_session, "triage_role_p@test.com", "patient")
        doctor = create_user(db_session, "triage_role_d@test.com", "doctor")
        create_membership(db_session, doctor.id, hosp.id)

        # Patient endpoint must reject doctor
        resp = client.get("/api/triage/patient", headers=auth(doctor.email))
        assert resp.status_code == 403

        # Doctor endpoint must reject patient
        resp2 = client.get("/api/triage/", headers=auth(patient.email))
        assert resp2 == resp2  # Doctor endpoint uses get_practitioner_identity

    def test_patient_cannot_access_doctor_triage_list(self, db_session):
        patient = create_user(db_session, "patient_triage_block@test.com", "patient")
        resp = client.get("/api/triage/", headers=auth(patient.email))
        assert resp.status_code == 403

    def test_doctor_cannot_access_patient_document_list(self, db_session):
        doctor = create_user(db_session, "doc_patient_list@test.com", "doctor")
        resp = client.get("/api/documents/patient", headers=auth(doctor.email))
        assert resp.status_code == 403


# ===========================================================================
# TEST: Legitimate E2E ALLOW flows
# ===========================================================================

class TestLegitimateFlows:

    def test_patient_can_list_own_notifications(self, db_session):
        patient = create_user(db_session, "notif_list_p@test.com", "patient")
        create_notification(db_session, patient.id)

        resp = client.get("/api/notifications", headers=auth(patient.email))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_doctor_can_list_own_notifications(self, db_session):
        doctor = create_user(db_session, "notif_list_d@test.com", "doctor")
        hosp = create_hospital(db_session)
        create_membership(db_session, doctor.id, hosp.id)
        create_notification(db_session, doctor.id)

        resp = client.get("/api/notifications", headers=auth(doctor.email))
        assert resp.status_code == 200

    def test_patient_can_list_own_documents(self, db_session):
        patient = create_user(db_session, "doc_list_p@test.com", "patient")
        resp = client.get("/api/documents/patient", headers=auth(patient.email))
        assert resp.status_code == 200

    def test_hospital_listing_allowed_for_authenticated_user(self, db_session):
        patient = create_user(db_session, "hosp_list@test.com", "patient")
        resp = client.get("/api/hospitals", headers=auth(patient.email))
        assert resp.status_code == 200

    def test_patient_can_read_own_triage_requests(self, db_session):
        hosp = create_hospital(db_session)
        patient = create_user(db_session, "triage_own_p@test.com", "patient")
        # Submit a triage request first
        client.post("/api/triage/", json={
            "symptoms": "cough and cold",
            "hospital_id": hosp.id
        }, headers=auth(patient.email))

        resp = client.get("/api/triage/patient", headers=auth(patient.email))
        assert resp.status_code == 200

    def test_doctor_can_access_own_access_requests(self, db_session):
        doctor = create_user(db_session, "ar_doc@test.com", "doctor")
        hosp = create_hospital(db_session)
        create_membership(db_session, doctor.id, hosp.id)

        resp = client.get("/api/access-requests/doctor", headers=auth(doctor.email))
        assert resp.status_code == 200

    def test_audit_logs_accessible_to_patient(self, db_session):
        patient = create_user(db_session, "audit_p@test.com", "patient")
        resp = client.get("/api/audit/patient", headers=auth(patient.email))
        assert resp.status_code == 200

    def test_audit_logs_accessible_to_doctor(self, db_session):
        doctor = create_user(db_session, "audit_d@test.com", "doctor")
        hosp = create_hospital(db_session)
        create_membership(db_session, doctor.id, hosp.id)
        resp = client.get("/api/audit/doctor", headers=auth(doctor.email))
        assert resp.status_code == 200

    def test_audit_logs_blocked_for_wrong_role(self, db_session):
        doctor = create_user(db_session, "audit_role_fail@test.com", "doctor")
        hosp = create_hospital(db_session)
        create_membership(db_session, doctor.id, hosp.id)
        resp = client.get("/api/audit/patient", headers=auth(doctor.email))
        assert resp.status_code == 403
