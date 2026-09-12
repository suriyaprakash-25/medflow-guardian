import pytest
from datetime import datetime
from app.services.consent import ConsentService
from app.services.authorization import AuthorizationContext, Operation, ResourceType, DenialReason
from app.models.user import User
from app.models.consent import Consent

class MockPolicyVersion:
    def __init__(self, payload):
        self.policy_payload = payload

class MockConsentState:
    def __init__(self, state_id, status, policy):
        self.id = state_id
        self.status = status
        self.policy_version = policy

class MockConsent:
    def __init__(self, patient_id=1, doctor_id=2, hospital_id=None):
        self.patient_id = patient_id
        self.doctor_id = doctor_id
        self.hospital_id = hospital_id

class MockQuery:
    def __init__(self, state):
        self.state = state
    def filter(self, *args, **kwargs):
        return self
    def order_by(self, *args, **kwargs):
        return self
    def first(self):
        return self.state

class MockDB:
    def __init__(self, authoritative_state):
        self.state = authoritative_state
    def query(self, model):
        return MockQuery(MockConsent() if model is Consent else self.state)

class MockRelationshipContext:
    def __init__(self, consent_id):
        self.consent_id = consent_id

def test_consent_service_allows_valid_request():
    policy = MockPolicyVersion({"allowed_purposes": ["TREATMENT"], "allowed_operations": ["download"]})
    state = MockConsentState(state_id=43, status="active", policy=policy)
    db = MockDB(state)
    svc = ConsentService(db)

    actor = User(id=2, role="doctor")
    ctx = AuthorizationContext(
        actor=actor,
        operation=Operation.DOWNLOAD,
        resource_type=ResourceType.DOCUMENT,
        db=db,
        patient_id=1,
        relationship_context=MockRelationshipContext(consent_id=10)
    )

    # Request matches authoritative state 43 and purpose TREATMENT
    decision = svc.evaluate(ctx, purpose="TREATMENT")
    assert decision.allowed is True


def test_consent_service_denies_revoked_consent():
    policy = MockPolicyVersion({"allowed_purposes": ["TREATMENT"], "allowed_operations": ["download"]})
    # Authoritative state is revoked
    state = MockConsentState(state_id=44, status="revoked", policy=policy)
    db = MockDB(state)
    svc = ConsentService(db)

    actor = User(id=2, role="doctor")
    ctx = AuthorizationContext(
        actor=actor,
        operation=Operation.DOWNLOAD,
        resource_type=ResourceType.DOCUMENT,
        db=db,
        patient_id=1,
        relationship_context=MockRelationshipContext(consent_id=10)
    )

    decision = svc.evaluate(ctx, purpose="TREATMENT")
    assert decision.allowed is False
    assert decision.reason == DenialReason.OPERATION_NOT_ALLOWED
    assert "revoked" in decision.detail

def test_consent_service_denies_invalid_purpose():
    policy = MockPolicyVersion({"allowed_purposes": ["TREATMENT"], "allowed_operations": ["download"]})
    state = MockConsentState(state_id=43, status="active", policy=policy)
    db = MockDB(state)
    svc = ConsentService(db)

    actor = User(id=2, role="doctor")
    ctx = AuthorizationContext(
        actor=actor,
        operation=Operation.DOWNLOAD,
        resource_type=ResourceType.DOCUMENT,
        db=db,
        patient_id=1,
        relationship_context=MockRelationshipContext(consent_id=10)
    )

    # Doctor requests with BILLING purpose
    decision = svc.evaluate(ctx, purpose="BILLING")
    assert decision.allowed is False
    assert decision.reason == DenialReason.OPERATION_NOT_ALLOWED
    assert "PURPOSE_NOT_ALLOWED" in decision.detail
