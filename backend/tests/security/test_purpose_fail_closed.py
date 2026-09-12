"""R4 regression tests for fail-closed purpose enforcement.

The governing invariant is RIGHT PURPOSE: once a non-patient actor reaches the
consent layer for patient-bound access, a missing/blank purpose must not bypass
policy evaluation. Patient self-access and operations with no patient subject
remain outside this cross-role purpose requirement.
"""

import pytest
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState, ConsentStatus
from app.models.hospital import Hospital, HospitalStaff
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    DenialReason,
    Operation,
    ResourceType,
)
from app.services.consent import ConsentService


class ConsentRelationship:
    def __init__(self, consent_id: int):
        self.consent_id = consent_id


def _user(db: Session, email: str, role: str) -> User:
    user = User(
        email=email,
        hashed_password="r4-test",
        full_name=email.split("@")[0],
        role=role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


def _active_consent(
    db: Session,
    *,
    patient: User,
    doctor: User,
    hospital: Hospital | None = None,
) -> tuple[Consent, ConsentPolicyVersion, ConsentState]:
    consent = Consent(
        patient_id=patient.id,
        doctor_id=doctor.id,
        hospital_id=hospital.id if hospital else None,
        status=ConsentStatus.ACTIVE.value,
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={
            "allowed_purposes": ["TREATMENT"],
            "allowed_operations": [Operation.READ.value],
        },
        status="active",
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status=ConsentStatus.ACTIVE.value,
    )
    db.add(state)
    db.commit()
    db.refresh(consent)
    db.refresh(policy)
    db.refresh(state)
    return consent, policy, state


def _doctor_context(
    db: Session,
    *,
    doctor: User,
    patient: User,
    consent: Consent,
    hospital: Hospital | None = None,
    purpose=None,
) -> AuthorizationContext:
    return AuthorizationContext(
        actor=doctor,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db,
        patient_id=patient.id,
        hospital_id=hospital.id if hospital else None,
        consent_id=consent.id,
        relationship_context=ConsentRelationship(consent.id),
        purpose=purpose,
    )


@pytest.mark.parametrize("missing_purpose", [None, "", "   "])
def test_cross_role_patient_access_denies_missing_or_blank_purpose(
    db_session: Session,
    missing_purpose,
):
    patient = _user(db_session, f"r4-patient-{repr(missing_purpose)}@example.com", "patient")
    doctor = _user(db_session, f"r4-doctor-{repr(missing_purpose)}@example.com", "doctor")
    consent, policy, state = _active_consent(
        db_session,
        patient=patient,
        doctor=doctor,
    )

    ctx = _doctor_context(
        db_session,
        doctor=doctor,
        patient=patient,
        consent=consent,
        purpose=missing_purpose,
    )
    decision = ConsentService(db_session).evaluate(ctx, missing_purpose)

    assert decision.allowed is False
    assert decision.reason == DenialReason.INVALID_CONTEXT
    assert "PURPOSE_REQUIRED" in decision.detail
    # Governance snapshot must still identify the authoritative state/policy
    # used for the denial so the resulting audit decision is explainable.
    assert ctx.consent_id == consent.id
    assert ctx.consent_state_id == state.id
    assert ctx.policy_version == policy.version_number


def test_cross_role_patient_access_with_valid_purpose_still_allows(db_session: Session):
    patient = _user(db_session, "r4-valid-patient@example.com", "patient")
    doctor = _user(db_session, "r4-valid-doctor@example.com", "doctor")
    consent, _, _ = _active_consent(db_session, patient=patient, doctor=doctor)

    ctx = _doctor_context(
        db_session,
        doctor=doctor,
        patient=patient,
        consent=consent,
        purpose="TREATMENT",
    )
    decision = ConsentService(db_session).evaluate(ctx, "TREATMENT")

    assert decision.allowed is True


def test_wrong_purpose_remains_policy_denial_not_missing_context(db_session: Session):
    patient = _user(db_session, "r4-wrong-purpose-patient@example.com", "patient")
    doctor = _user(db_session, "r4-wrong-purpose-doctor@example.com", "doctor")
    consent, _, _ = _active_consent(db_session, patient=patient, doctor=doctor)

    ctx = _doctor_context(
        db_session,
        doctor=doctor,
        patient=patient,
        consent=consent,
        purpose="BILLING",
    )
    decision = ConsentService(db_session).evaluate(ctx, "BILLING")

    assert decision.allowed is False
    assert decision.reason == DenialReason.OPERATION_NOT_ALLOWED
    assert "PURPOSE_NOT_ALLOWED" in decision.detail


def test_patient_self_access_does_not_require_cross_role_purpose(db_session: Session):
    patient = _user(db_session, "r4-self-patient@example.com", "patient")
    db_session.commit()

    ctx = AuthorizationContext(
        actor=patient,
        operation=Operation.READ,
        resource_type=ResourceType.PATIENT_RECORD,
        db=db_session,
        patient_id=patient.id,
        purpose=None,
    )
    decision = ConsentService(db_session).evaluate(ctx, None)

    assert decision.allowed is True


def test_non_patient_subject_operation_does_not_invent_consent_requirement(db_session: Session):
    platform_admin = _user(db_session, "r4-platform-admin@example.com", "platform_admin")
    db_session.commit()

    ctx = AuthorizationContext(
        actor=platform_admin,
        operation=Operation.READ,
        resource_type=ResourceType.HOSPITAL,
        db=db_session,
        patient_id=None,
        purpose=None,
    )
    decision = ConsentService(db_session).evaluate(ctx, None)

    assert decision.allowed is True


def test_cae_records_missing_purpose_as_denied_governed_access(db_session: Session):
    hospital = Hospital(name="R4 Purpose Hospital")
    db_session.add(hospital)
    db_session.flush()

    patient = _user(db_session, "r4-cae-patient@example.com", "patient")
    doctor = _user(db_session, "r4-cae-doctor@example.com", "doctor")
    db_session.add(
        HospitalStaff(
            user_id=doctor.id,
            hospital_id=hospital.id,
            role="doctor",
            is_active=True,
        )
    )
    consent, policy, state = _active_consent(
        db_session,
        patient=patient,
        doctor=doctor,
        hospital=hospital,
    )

    ctx = _doctor_context(
        db_session,
        doctor=doctor,
        patient=patient,
        consent=consent,
        hospital=hospital,
        purpose=None,
    )
    decision = AuthorizationService(db_session).authorize(ctx)

    assert decision.allowed is False
    assert decision.reason == DenialReason.INVALID_CONTEXT
    assert "PURPOSE_REQUIRED" in decision.detail
    assert ctx.consent_state_id == state.id
    assert ctx.policy_version == policy.version_number

    audit = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.actor_id == doctor.id,
            AuditLog.patient_id == patient.id,
            AuditLog.consent_id == consent.id,
            AuditLog.operation == Operation.READ.value,
            AuditLog.resource_type == ResourceType.PATIENT_RECORD.value,
        )
        .order_by(AuditLog.id.desc())
        .first()
    )
    assert audit is not None
    assert audit.decision == "DENY"
    assert audit.denial_reason == DenialReason.INVALID_CONTEXT.value
    assert audit.consent_state_id == state.id
    assert audit.policy_version == policy.version_number
