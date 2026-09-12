from app.services.consent import ConsentService
from app.services.authorization import AuthorizationContext, Operation, ResourceType, DenialReason
from app.models.consent import Consent
from app.models.user import User


class MockPolicyVersion:
    def __init__(self, payload):
        self.policy_payload = payload


class MockConsentState:
    def __init__(self, state_id, status, policy):
        self.id = state_id
        self.status = status
        self.policy_version = policy


class MockQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self.result


class MockDB:
    def __init__(self, consent, authoritative_state):
        self.consent = consent
        self.state = authoritative_state

    def query(self, model):
        # ConsentService performs two different queries: first Consent, then
        # the authoritative ConsentState. Return the matching mock entity.
        if model is Consent:
            return MockQuery(self.consent)
        return MockQuery(self.state)


class MockRelationshipContext:
    def __init__(self, consent_id):
        self.consent_id = consent_id


def _context(db, actor_id=2, patient_id=1, consent_id=10):
    actor = User(id=actor_id, role="doctor")
    return AuthorizationContext(
        actor=actor,
        operation=Operation.DOWNLOAD,
        resource_type=ResourceType.DOCUMENT,
        db=db,
        patient_id=patient_id,
        relationship_context=MockRelationshipContext(consent_id=consent_id),
    )


def _db(status="active"):
    policy = MockPolicyVersion({
        "allowed_purposes": ["TREATMENT"],
        "allowed_operations": [Operation.DOWNLOAD.value],
    })
    state = MockConsentState(state_id=43, status=status, policy=policy)
    consent = Consent(id=10, patient_id=1, doctor_id=2, hospital_id=None, status=status)
    return MockDB(consent, state)


def test_consent_service_allows_valid_request():
    db = _db()
    decision = ConsentService(db).evaluate(_context(db), purpose="TREATMENT")
    assert decision.allowed is True


def test_consent_service_denies_revoked_consent():
    db = _db(status="revoked")
    decision = ConsentService(db).evaluate(_context(db), purpose="TREATMENT")
    assert decision.allowed is False
    assert decision.reason == DenialReason.OPERATION_NOT_ALLOWED
    assert "revoked" in decision.detail


def test_consent_service_denies_invalid_purpose():
    db = _db()
    decision = ConsentService(db).evaluate(_context(db), purpose="BILLING")
    assert decision.allowed is False
    assert decision.reason == DenialReason.OPERATION_NOT_ALLOWED
    assert "PURPOSE_NOT_ALLOWED" in decision.detail
