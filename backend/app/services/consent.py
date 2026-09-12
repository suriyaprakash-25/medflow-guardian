from typing import Optional
from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentState, ConsentStatus
from app.services.authorization import AuthorizationContext, AuthorizationDecision, DenialReason

class ConsentService:
    """
    Policy Evaluation Engine for MedFlow Guardian Phase 5.
    Evaluates Purpose and checks Enforcement State against Authoritative Consent State.
    """
    def __init__(self, db: Session):
        self._db = db

    def evaluate(
        self, 
        ctx: AuthorizationContext, 
        purpose: Optional[str]
    ) -> AuthorizationDecision:
        """
        Evaluate if the current operation is permitted by the patient's active consent policy.
        Also enforces the strict Stale-State Rule if an enforcement point is verifying its state.
        """
        # 1. Identify if this operation requires consent evaluation.
        # Generally, a doctor accessing a patient's document requires consent evaluation.
        # If the actor is the patient themselves, they don't need a consent policy to access their own data.
        if ctx.actor.role == "patient" and ctx.patient_id == ctx.actor.id:
            return AuthorizationDecision.allow()

        # If there's no patient context, consent doesn't apply (e.g. listing hospitals)
        if not ctx.patient_id:
            return AuthorizationDecision.allow()

        # 2. Extract explicit consent context. New routes use ctx.consent_id;
        # relationship_context remains supported for document grants and older
        # enforcement points while they migrate to the explicit field.
        consent_id = ctx.consent_id
        if not consent_id:
            consent_id = getattr(ctx.relationship_context, "consent_id", None)
        if not consent_id:
            # Try to see if relationship_context IS the consent_id
            if isinstance(ctx.relationship_context, int):
                consent_id = ctx.relationship_context

        if not consent_id:
            # If no consent is provided for cross-role access, and it's a sensitive operation, deny.
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT, 
                "No consent context provided for cross-role access"
            )

        # Bind the supplied consent to the exact patient, practitioner, and
        # organization in the trusted authorization context before evaluating
        # its policy. A valid consent ID for another subject must never work.
        consent = self._db.query(Consent).filter(Consent.id == consent_id).first()
        if not consent:
            return AuthorizationDecision.deny(
                DenialReason.CONSENT_REQUIRED, "Consent context was not found"
            )
        if consent.patient_id != ctx.patient_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT, "Consent is bound to another patient"
            )
        if consent.doctor_id is not None and (
            ctx.actor.role != "doctor" or consent.doctor_id != ctx.actor.id
        ):
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT, "Consent is bound to another doctor/practitioner"
            )
        if consent.hospital_id is not None and consent.hospital_id != ctx.hospital_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is bound to another hospital/organization",
            )
        # 3. Load the Authoritative Consent State (the latest state row)
        authoritative_state = self._db.query(ConsentState).filter(
            ConsentState.consent_id == consent_id
        ).order_by(ConsentState.created_at.desc(), ConsentState.id.desc()).first()

        if not authoritative_state:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT, "Consent state history is missing"
            )

        # Populate the exact governance snapshot before any policy denial so
        # both ALLOW and DENY audit rows remain explainable.
        policy = authoritative_state.policy_version
        ctx.consent_id = consent_id
        ctx.consent_state_id = authoritative_state.id
        ctx.policy_version = getattr(policy, "version_number", None)

        # 4. ENFORCEMENT STATE STALE-STATE RULE
        # Removed: Backend is a collocated PEP.

        # 5. Check if Consent is actually ACTIVE
        if authoritative_state.status != ConsentStatus.ACTIVE.value:
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED, 
                f"Consent is currently {authoritative_state.status}"
            )

        # 6. Load the active Policy Version
        if not policy:
            return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "Policy version not found")

        # 7. Purpose Evaluation
        if purpose:
            allowed_purposes = policy.policy_payload.get("allowed_purposes", [])
            if purpose not in allowed_purposes:
                return AuthorizationDecision.deny(
                    DenialReason.OPERATION_NOT_ALLOWED,
                    f"PURPOSE_NOT_ALLOWED: '{purpose}' is not permitted by the active consent policy"
                )

        # 8. Operation Evaluation
        allowed_operations = policy.policy_payload.get("allowed_operations", [])
        if allowed_operations and ctx.operation.value not in allowed_operations:
             return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                f"OPERATION_NOT_ALLOWED: '{ctx.operation.value}' is not permitted by the active consent policy"
            )

        return AuthorizationDecision.allow()
