"""Phase 5.5 adversarial consent authorization regression tests.

These tests exercise the consent layer inside the Model A collocated CAE/PEP
boundary. They intentionally probe identity, relationship, lifecycle, purpose,
and operation binding rather than testing only the happy path.
"""

from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    DenialReason,
    Operation,
    ResourceType,
)
from app.services.consent import ConsentService


class Relationship:
    def __init__(self, consent_id, patient_id=None, doctor_id=None, hospital_id=None):
        self.consent_id = consent_id
        self.patient_id = patient_id
        self.doctor_id = doctor_id
        self.hospital_id = hospital_id


def _user(db: Session, email: str, role: str) -> User:
    user = User(
        email=email,
        full_name=email.split("@")[0],
        role=role,
        is_active=True,
        hashed_password="phase5_5_test",
    )
    db.add(user)
    db.flush()
    return user


def _consent(db: Session, patient: User, doctor: User, hospital: Hospital | None = None,
             status: str = ConsentStatus.ACTIVE.value,
             purposes=None, operations=None):
    consent = Consent(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id if hospital else None,
        status=status,
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": purposes or ["TREATMENT"],
            "allowed_operations": operations or [Operation.READ.value],
        },
        status="active",
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=status,
    )
    db.add(state)
    db.commit()
    db.refresh(consent)
    return consent, policy, state


def _ctx(db, doctor, patient_id, consent_id, purpose="TREATMENT", hospital_id=None):
    return AuthorizationContext(
        actor=doctor,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=patient_id,
        relationship_context=Relationship(
            consent_id=consent_id,
            patient_id=patient_id,
            doctor_id=doctor.id,
            hospital_id=hospital_id,
        ),
        purpose=purpose,
    )


def test_valid_consent_allows_bound_doctor(db_session: Session):
    patient = _user(db_session, "p55-valid@example.com", "patient")
    doctor = _user(db_session, "d55-valid@example.com", "doctor")
    consent, _, _ = _consent(db_session, patient, doctor)

    decision = ConsentService(db_session).evaluate(
        _ctx(db_session, doctor, patient.id, consent.id), "TREATMENT"
    )

    assert decision.allowed is True


def test_wrong_patient_cannot_reuse_valid_consent(db_session: Session):
    patient = _user(db_session, "p55-owner@example.com", "patient")
    other_patient = _user(db_session, "p55-other@example.com", "patient")
    doctor = _user(db_session, "d55-patient@example.com", "doctor")
    consent, _, _ = _consent(db_session, patient, doctor)

    decision = ConsentService(db_session).evaluate(
        _ctx(db_session, doctor, other_patient.id, consent.id), "TREATMENT"
    )

    assert decision.allowed is False
    assert decision.reason == DenialReason.INVALID_CONTEXT
    assert "patient" in decision.detail.lower()


def test_wrong_doctor_cannot_reuse_valid_consent(db_session: Session):
    patient = _user(db_session, "p55-doctor-owner@example.com", "patient")
    doctor = _user(db_session, "d55-authorized@example.com", "doctor")
    attacker = _user(db_session, "d55-attacker@example.com", "doctor")
    consent, _, _ = _consent(db_session, patient, doctor)

    decision = ConsentService(db_session).evaluate(
        _ctx(db_session, attacker, patient.id, consent.id), "TREATMENT"
    )

    assert decision.allowed is False
    assert decision.reason == DenialReason.INVALID_CONTEXT
    assert "doctor" in decision.detail.lower()


def test_wrong_hospital_cannot_reuse_hospital_bound_consent(db_session: Session):
    patient = _user(db_session, "p55-hospital-owner@example.com", "patient")
    doctor = _user(db_session, "d55-hospital@example.com", "doctor")
    hospital_a = Hospital(name="Phase 5.5 Hospital A")
    hospital_b = Hospital(name="Phase 5.5 Hospital B")
    db_session.add_all([hospital_a, hospital_b])
    db_session.flush()
    db_session.add(HospitalStaff(user_id=doctor.id, hospital_id=hospital_a.id, role="doctor", is_active=True))
    db_session.commit()

    consent, _, _ = _consent(db_session, patient, doctor, hospital=hospital_a)

    decision = ConsentService(db_session).evaluate(
        _ctx(db_session, doctor, patient.id, consent.id, hospital_id=hospital_b.id),
        "TREATMENT",
    )

    assert decision.allowed is False
    assert decision.reason == DenialReason.INVALID_CONTEXT
    assert "hospital" in decision.detail.lower()


def test_revoked_and_suspended_consent_fail_closed(db_session: Session):
    patient = _user(db_session, "p55-lifecycle@example.com", "patient")
    doctor = _user(db_session, "d55-lifecycle@example.com", "doctor")

    for index, status in enumerate((ConsentStatus.REVOKED.value, ConsentStatus.SUSPENDED.value)):
        consent, _, _ = _consent(
            db_session, patient, doctor, status=status,
            purposes=["TREATMENT"], operations=[Operation.READ.value],
        )
        decision = ConsentService(db_session).evaluate(
            _ctx(db_session, doctor, patient.id, consent.id), "TREATMENT"
        )
        assert decision.allowed is False, f"lifecycle case {index} unexpectedly allowed"
        assert decision.reason == DenialReason.OPERATION_NOT_ALLOWED
        assert status in decision.detail


def test_disallowed_purpose_and_operation_fail_closed(db_session: Session):
    patient = _user(db_session, "p55-policy@example.com", "patient")
    doctor = _user(db_session, "d55-policy@example.com", "doctor")
    consent, _, _ = _consent(
        db_session,
        patient,
        doctor,
        purposes=["TREATMENT"],
        operations=[Operation.READ.value],
    )
    service = ConsentService(db_session)

    purpose_denied = service.evaluate(
        _ctx(db_session, doctor, patient.id, consent.id, purpose="BILLING"), "BILLING"
    )
    assert purpose_denied.allowed is False
    assert "PURPOSE_NOT_ALLOWED" in purpose_denied.detail

    operation_ctx = _ctx(db_session, doctor, patient.id, consent.id)
    operation_ctx.operation = Operation.DOWNLOAD
    operation_denied = service.evaluate(operation_ctx, "TREATMENT")
    assert operation_denied.allowed is False
    assert "OPERATION_NOT_ALLOWED" in operation_denied.detail


def test_new_policy_version_becomes_authoritative_without_mutating_v1(db_session: Session):
    patient = _user(db_session, "p55-versioning@example.com", "patient")
    doctor = _user(db_session, "d55-versioning@example.com", "doctor")
    consent, policy_v1, state_v1 = _consent(
        db_session, patient, doctor, purposes=["TREATMENT"], operations=[Operation.READ.value]
    )

    policy_v2 = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=2,
        policy_payload={
            "allowed_purposes": ["TREATMENT", "EMERGENCY"],
            "allowed_operations": [Operation.READ.value, Operation.DOWNLOAD.value],
        },
        status="active",
    )
    policy_v1.status = "superseded"
    db_session.add(policy_v2)
    db_session.flush()
    state_v2 = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy_v2.id,
        status=ConsentStatus.ACTIVE.value,
        reason="Expanded treatment policy",
    )
    db_session.add(state_v2)
    db_session.commit()

    db_session.refresh(policy_v1)
    db_session.refresh(state_v1)
    db_session.refresh(state_v2)

    assert policy_v1.version_number == 1
    assert policy_v1.policy_payload == {
        "allowed_purposes": ["TREATMENT"],
        "allowed_operations": [Operation.READ.value],
    }
    assert policy_v1.status == "superseded"
    assert state_v2.policy_version_id == policy_v2.id
    assert state_v2.reason == "Expanded treatment policy"

    # The authoritative state is v2, so the newly granted operation is allowed.
    download_ctx = _ctx(db_session, doctor, patient.id, consent.id)
    download_ctx.operation = Operation.DOWNLOAD
    decision = ConsentService(db_session).evaluate(download_ctx, "EMERGENCY")
    assert decision.allowed is True
