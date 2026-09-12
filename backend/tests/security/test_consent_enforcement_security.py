import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.consent import Consent, ConsentState, ConsentPolicyVersion, ConsentStatus
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType, DenialReason

def test_consent_evaluation_enforcement_stale(db_session: Session):
    """
    STALE ENFORCEMENT STATE TEST:
    If authoritative state is 43, but enforcement state is 42, it must fail closed.
    """
    svc = AuthorizationService(db_session)
    # create mock patient and doctor
    patient = User(email="testpatient_sec1@example.com", full_name="Patient 1", role="patient", is_active=True, hashed_password="x")
    doctor = User(email="testdoctor_sec1@example.com", full_name="Doctor 1", role="doctor", is_active=True, hashed_password="x")
    db_session.add(patient)
    db_session.add(doctor)
    db_session.commit()

    # create consent
    consent = Consent(patient_id=patient.id, status=ConsentStatus.ACTIVE.value)
    db_session.add(consent)
    db_session.flush()

    policy = ConsentPolicyVersion(consent_id=consent.id, version_number=1, policy_payload={"allowed_purposes": ["TREATMENT"], "allowed_operations": ["read"]}, status="active")
    db_session.add(policy)
    db_session.flush()

    state1 = ConsentState(consent_id=consent.id, policy_version_id=policy.id, status=ConsentStatus.ACTIVE.value)
    db_session.add(state1)
    db_session.commit()
    db_session.refresh(state1)

    # Now we have an active consent with state1.id
    ctx = AuthorizationContext(
        actor=doctor,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db_session,
        patient_id=patient.id,
        relationship_context=consent.id,
        purpose="TREATMENT"
    )
    decision = svc.authorize(ctx)
    assert decision.allowed == True, "Should allow when enforcement state is current and active"

    # Now we create a new state (authoritative state changes to N+1)
    state2 = ConsentState(consent_id=consent.id, policy_version_id=policy.id, status=ConsentStatus.REVOKED.value)
    db_session.add(state2)
    consent.status = ConsentStatus.REVOKED.value
    db_session.commit()
    db_session.refresh(state2)


    # Doctor retries but consent is REVOKED
    ctx_revoked = AuthorizationContext(
        actor=doctor,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db_session,
        patient_id=patient.id,
        relationship_context=consent.id,
        purpose="TREATMENT"
    )
    decision_revoked = svc.authorize(ctx_revoked)
    assert decision_revoked.allowed == False
    assert decision_revoked.reason == DenialReason.OPERATION_NOT_ALLOWED
    assert "Consent is currently revoked" in decision_revoked.detail

def test_purpose_mismatch(db_session: Session):
    svc = AuthorizationService(db_session)
    patient = User(email="testpatient_sec2@example.com", full_name="Patient 2", role="patient", is_active=True, hashed_password="x")
    doctor = User(email="testdoctor_sec2@example.com", full_name="Doctor 2", role="doctor", is_active=True, hashed_password="x")
    db_session.add(patient)
    db_session.add(doctor)
    db_session.commit()

    consent = Consent(patient_id=patient.id, status=ConsentStatus.ACTIVE.value)
    db_session.add(consent)
    db_session.flush()

    policy = ConsentPolicyVersion(consent_id=consent.id, version_number=1, policy_payload={"allowed_purposes": ["TREATMENT"]}, status="active")
    db_session.add(policy)
    db_session.flush()

    state = ConsentState(consent_id=consent.id, policy_version_id=policy.id, status=ConsentStatus.ACTIVE.value)
    db_session.add(state)
    db_session.commit()
    db_session.refresh(state)

    # Valid purpose
    ctx = AuthorizationContext(
        actor=doctor,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db_session,
        patient_id=patient.id,
        relationship_context=consent.id,
        purpose="TREATMENT"
    )
    decision = svc.authorize(ctx)
    assert decision.allowed == True

    # Invalid purpose
    ctx_invalid = AuthorizationContext(
        actor=doctor,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db_session,
        patient_id=patient.id,
        relationship_context=consent.id,
        purpose="MARKETING"
    )
    decision_invalid = svc.authorize(ctx_invalid)
    assert decision_invalid.allowed == False
    assert "PURPOSE_NOT_ALLOWED" in decision_invalid.detail
