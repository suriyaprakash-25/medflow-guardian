"""
Phase 4 — Central Authorization Engine Unit Tests

Tests the AuthorizationService directly without HTTP.
Covers: DEFAULT DENY, role enforcement, ownership, organization isolation,
relationship requirements, all resource types.
"""
from datetime import datetime, timedelta

from app.services.authorization import (
    AuthorizationService,
    AuthorizationContext,
    AuthorizationDecision,
    DenialReason,
    Operation,
    ResourceType,
)
from app.models.user import User
from app.models.hospital import HospitalStaff
from app.models.document import MedicalDocument
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.notification import Notification


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_user(role="doctor", is_active=True, user_id=1):
    u = User()
    u.id = user_id
    u.email = f"user{user_id}@test.com"
    u.full_name = "Test User"
    u.role = role
    u.is_active = is_active
    return u


def make_document(patient_id=10, hospital_id=1, uploader_id=1, doc_id=100):
    doc = MedicalDocument()
    doc.id = doc_id
    doc.patient_id = patient_id
    doc.hospital_id = hospital_id
    doc.uploaded_by_doctor_id = uploader_id
    doc.title = "Test Doc"
    doc.status = "active"
    return doc


def make_triage(patient_id=10, hospital_id=1, triage_id=50):
    from app.models.triage import TriageRequest
    t = TriageRequest()
    t.id = triage_id
    t.patient_id = patient_id
    t.hospital_id = hospital_id
    t.status = "pending"
    return t


def make_access_request(patient_id=10, doctor_id=1, hospital_id=1, status="pending", req_id=200):
    req = DocumentAccessRequest()
    req.id = req_id
    req.patient_id = patient_id
    req.requesting_doctor_id = doctor_id
    req.requesting_hospital_id = hospital_id
    req.status = status
    req.requested_documents = []
    return req


def make_access_grant(patient_id=10, doctor_id=1, hospital_id=1, status="active", grant_id=300):
    grant = DocumentAccessGrant()
    grant.id = grant_id
    grant.patient_id = patient_id
    grant.doctor_id = doctor_id
    grant.hospital_id = hospital_id
    grant.status = status
    grant.expires_at = datetime.utcnow() + timedelta(hours=24)
    grant.granted_documents = []
    return grant


def make_notification(user_id=10, notif_id=400):
    n = Notification()
    n.id = notif_id
    n.user_id = user_id
    n.message = "Test notification"
    n.is_read = False
    return n


class MockDB:
    """Minimal SQLAlchemy session/query mock for authorization unit tests."""

    def __init__(self, membership=None, visit=None, grant=None):
        self._membership = membership
        self._visit = visit
        self._grant = grant

    def query(self, model):
        return self

    def filter(self, *args):
        return self

    def order_by(self, *args):
        # Production grant resolution orders candidates before materializing them.
        # The unit mock does not evaluate SQL expressions, but it must preserve the
        # SQLAlchemy query-chain contract instead of forcing production code to
        # special-case tests.
        return self

    def all(self):
        # `_get_active_grant` now inspects all active grant candidates. Preserve
        # the existing fixture contract while allowing either one grant or a list.
        if self._grant is None:
            return []
        value = self._grant
        self._grant = None
        if isinstance(value, (list, tuple)):
            return list(value)
        return [value]

    def first(self):
        # Return membership or visit based on what was set
        if self._membership is not None:
            val = self._membership
            self._membership = None  # consume once
            return val
        if self._visit is not None:
            val = self._visit
            self._visit = None
            return val
        if self._grant is not None:
            val = self._grant
            self._grant = None
            return val
        return None


def make_svc(db=None):
    if db is None:
        db = MockDB()
    return AuthorizationService(db)


# ===========================================================================
# TEST: DEFAULT DENY
# ===========================================================================

def test_default_deny_no_actor():
    svc = make_svc()
    ctx = AuthorizationContext(
        actor=None,
        operation=Operation.READ,
        resource_type=ResourceType.DOCUMENT,
        db=MockDB()
    )
    d = svc.authorize(ctx)
    assert not d.allowed
    assert d.reason == DenialReason.AUTHENTICATION_REQUIRED


def test_default_deny_inactive_user():
    svc = make_svc()
    actor = make_user(is_active=False)
    ctx = AuthorizationContext(
        actor=actor,
        operation=Operation.READ,
        resource_type=ResourceType.DOCUMENT,
        db=MockDB()
    )
    d = svc.authorize(ctx)
    assert not d.allowed
    assert d.reason == DenialReason.USER_INACTIVE


def test_default_deny_unknown_resource_type():
    svc = make_svc()
    actor = make_user()
    ctx = AuthorizationContext(
        actor=actor,
        operation=Operation.READ,
        resource_type="totally_unknown_type",  # type: ignore
        db=MockDB()
    )
    d = svc.authorize(ctx)
    assert not d.allowed


# ===========================================================================
# TEST: DOCUMENT
# ===========================================================================

class TestDocumentAuthorization:

    def test_doctor_upload_with_valid_membership(self):
        membership = HospitalStaff()
        membership.hospital_id = 1
        membership.is_active = True
        db = MockDB(membership=membership)
        svc = make_svc(db)
        actor = make_user(role="doctor")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db, hospital_id=1
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_doctor_upload_no_membership_denied(self):
        db = MockDB(membership=None)
        svc = make_svc(db)
        actor = make_user(role="doctor")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db, hospital_id=1
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.MEMBERSHIP_REQUIRED

    def test_patient_cannot_upload(self):
        svc = make_svc()
        actor = make_user(role="patient")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=MockDB(), hospital_id=1
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED

    def test_patient_downloads_own_document(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        doc = make_document(patient_id=10)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=MockDB(), resource=doc
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_patient_cannot_download_other_patient_document(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        doc = make_document(patient_id=99)  # Different patient
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=MockDB(), resource=doc
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.RESOURCE_NOT_OWNED

    def test_doctor_downloads_own_hospital_document(self):
        membership = HospitalStaff(); membership.hospital_id = 1; membership.is_active = True
        db = MockDB(membership=membership)
        svc = make_svc(db)
        actor = make_user(role="doctor", user_id=1)
        doc = make_document(patient_id=10, hospital_id=1, uploader_id=5)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=db, resource=doc
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_doctor_cannot_download_other_hospital_document_no_grant(self):
        db = MockDB(membership=None, grant=None)
        svc = make_svc(db)
        actor = make_user(role="doctor", user_id=1)
        doc = make_document(patient_id=10, hospital_id=99, uploader_id=5)  # Different hospital, not uploader
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=db, resource=doc
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ORGANIZATION_MISMATCH

    def test_download_document_not_found(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=MockDB(), resource=None  # Not found
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.RESOURCE_NOT_FOUND


# ===========================================================================
# TEST: ACCESS_REQUEST
# ===========================================================================

class TestAccessRequestAuthorization:

    def test_doctor_can_request_access_with_membership(self):
        membership = HospitalStaff(); membership.hospital_id = 1; membership.is_active = True
        db = MockDB(membership=membership)
        svc = make_svc(db)
        actor = make_user(role="doctor")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REQUEST_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=db, hospital_id=1
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_doctor_cannot_request_access_without_membership(self):
        db = MockDB(membership=None)
        svc = make_svc(db)
        actor = make_user(role="doctor")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REQUEST_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=db, hospital_id=1
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.MEMBERSHIP_REQUIRED

    def test_patient_cannot_request_access(self):
        svc = make_svc()
        actor = make_user(role="patient")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REQUEST_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=MockDB(), hospital_id=1
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED

    def test_patient_approves_own_request(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        req = make_access_request(patient_id=10, status="pending")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.GRANT_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=MockDB(), resource=req
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_patient_cannot_approve_other_patient_request(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        req = make_access_request(patient_id=99, status="pending")  # Different patient
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.GRANT_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=MockDB(), resource=req
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.RESOURCE_NOT_OWNED

    def test_doctor_cannot_approve_request(self):
        svc = make_svc()
        actor = make_user(role="doctor")
        req = make_access_request(patient_id=10, status="pending")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.GRANT_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=MockDB(), resource=req
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED


# ===========================================================================
# TEST: ACCESS_GRANT (REVOKE)
# ===========================================================================

class TestAccessGrantAuthorization:

    def test_patient_revokes_own_grant(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        grant = make_access_grant(patient_id=10, status="active")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REVOKE_ACCESS,
            resource_type=ResourceType.ACCESS_GRANT,
            db=MockDB(), resource=grant
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_patient_cannot_revoke_other_patient_grant(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        grant = make_access_grant(patient_id=99, status="active")  # Different patient
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REVOKE_ACCESS,
            resource_type=ResourceType.ACCESS_GRANT,
            db=MockDB(), resource=grant
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.RESOURCE_NOT_OWNED

    def test_doctor_cannot_revoke_grant(self):
        svc = make_svc()
        actor = make_user(role="doctor")
        grant = make_access_grant(patient_id=10, status="active")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REVOKE_ACCESS,
            resource_type=ResourceType.ACCESS_GRANT,
            db=MockDB(), resource=grant
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED

    def test_cannot_revoke_inactive_grant(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        grant = make_access_grant(patient_id=10, status="revoked")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REVOKE_ACCESS,
            resource_type=ResourceType.ACCESS_GRANT,
            db=MockDB(), resource=grant
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.OPERATION_NOT_ALLOWED


# ===========================================================================
# TEST: TRIAGE
# ===========================================================================

class TestTriageAuthorization:

    def test_patient_can_create_triage(self):
        svc = make_svc()
        actor = make_user(role="patient")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.TRIAGE_REQUEST, db=MockDB()
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_doctor_cannot_create_triage(self):
        svc = make_svc()
        actor = make_user(role="doctor")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.TRIAGE_REQUEST, db=MockDB()
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED

    def test_doctor_can_update_own_hospital_triage(self):
        membership = HospitalStaff(); membership.hospital_id = 1; membership.is_active = True
        db = MockDB(membership=membership)
        svc = make_svc(db)
        actor = make_user(role="doctor")
        triage = make_triage(hospital_id=1)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.UPDATE_STATUS,
            resource_type=ResourceType.TRIAGE_REQUEST,
            db=db, resource=triage
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_doctor_cannot_update_other_hospital_triage(self):
        db = MockDB(membership=None)
        svc = make_svc(db)
        actor = make_user(role="doctor")
        triage = make_triage(hospital_id=99)  # Different hospital
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.UPDATE_STATUS,
            resource_type=ResourceType.TRIAGE_REQUEST,
            db=db, resource=triage
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.MEMBERSHIP_REQUIRED


# ===========================================================================
# TEST: NOTIFICATION (IDOR)
# ===========================================================================

class TestNotificationAuthorization:

    def test_user_reads_own_notification(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        notif = make_notification(user_id=10)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.MARK_READ,
            resource_type=ResourceType.NOTIFICATION,
            db=MockDB(), resource=notif
        )
        d = svc.authorize(ctx)
        assert d.allowed

    def test_user_cannot_read_other_user_notification(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        notif = make_notification(user_id=99)  # Different user
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.MARK_READ,
            resource_type=ResourceType.NOTIFICATION,
            db=MockDB(), resource=notif
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.RESOURCE_NOT_OWNED

    def test_notification_not_found_denied(self):
        svc = make_svc()
        actor = make_user(role="patient", user_id=10)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.MARK_READ,
            resource_type=ResourceType.NOTIFICATION,
            db=MockDB(), resource=None
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.RESOURCE_NOT_FOUND


# ===========================================================================
# TEST: ORGANIZATION ISOLATION
# ===========================================================================

class TestOrganizationIsolation:

    def test_cross_org_document_upload_denied(self):
        """Doctor in Hospital A cannot upload to Hospital B."""
        # Mock returns None (not a member of hospital 2)
        db = MockDB(membership=None)
        svc = make_svc(db)
        actor = make_user(role="doctor", user_id=1)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db,
            hospital_id=2  # Doctor is only in hospital 1
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.MEMBERSHIP_REQUIRED

    def test_inactive_membership_denied(self):
        """Inactive membership must be denied."""
        # MockDB returns None (is_active=False filtered out)
        db = MockDB(membership=None)
        svc = make_svc(db)
        actor = make_user(role="doctor", user_id=1)
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db, hospital_id=1
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.MEMBERSHIP_REQUIRED

    def test_hospital_listing_allowed_for_any_authenticated(self):
        svc = make_svc()
        for role in ("doctor", "patient"):
            actor = make_user(role=role)
            ctx = AuthorizationContext(
                actor=actor, operation=Operation.LIST,
                resource_type=ResourceType.HOSPITAL, db=MockDB()
            )
            d = svc.authorize(ctx)
            assert d.allowed


# ===========================================================================
# TEST: ROLE ESCALATION PREVENTION
# ===========================================================================

class TestRoleEscalation:

    def test_patient_cannot_update_triage_status(self):
        svc = make_svc()
        actor = make_user(role="patient")
        triage = make_triage()
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.UPDATE_STATUS,
            resource_type=ResourceType.TRIAGE_REQUEST,
            db=MockDB(), resource=triage
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED

    def test_patient_cannot_request_access(self):
        svc = make_svc()
        actor = make_user(role="patient")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.REQUEST_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=MockDB(), hospital_id=1
        )
        d = svc.authorize(ctx)
        assert not d.allowed

    def test_doctor_cannot_submit_reading(self):
        svc = make_svc()
        actor = make_user(role="doctor")
        ctx = AuthorizationContext(
            actor=actor, operation=Operation.CREATE,
            resource_type=ResourceType.PATIENT_READING,
            db=MockDB()
        )
        d = svc.authorize(ctx)
        assert not d.allowed
        assert d.reason == DenialReason.ROLE_NOT_PERMITTED


# ===========================================================================
# TEST: AuthorizationDecision model
# ===========================================================================

class TestDecisionModel:

    def test_allow_decision(self):
        d = AuthorizationDecision.allow()
        assert d.allowed is True
        assert d.reason is None

    def test_deny_decision(self):
        d = AuthorizationDecision.deny(DenialReason.MEMBERSHIP_REQUIRED, "test")
        assert d.allowed is False
        assert d.reason == DenialReason.MEMBERSHIP_REQUIRED
        assert d.detail == "test"

    def test_default_deny(self):
        d = AuthorizationDecision.default_deny()
        assert d.allowed is False
        assert d.reason == DenialReason.OPERATION_NOT_ALLOWED
