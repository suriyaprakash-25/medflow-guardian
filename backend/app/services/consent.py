from typing import Optional
from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentState, ConsentStatus
from app.services.authorization import AuthorizationContext, AuthorizationDecision, DenialReason


class ConsentService:
    """Policy evaluation for consent inside the collocated CAE/PEP boundary."""

    def __init__(self, db: Session):
        self._db = db

    def evaluate(
        self,
        ctx: AuthorizationContext,
        purpose: Optional[str],
    ) -> AuthorizationDecision:
        """Evaluate active consent and bind it to the authorization context."""
        if ctx.actor.role == "patient" and ctx.patient_id == ctx.actor.id:
            return AuthorizationDecision.allow()

        if not ctx.patient_id:
            return AuthorizationDecision.allow()

        relationship = ctx.relationship_context
        consent_id = getattr(relationship, "consent_id", None)
        if not consent_id and isinstance(relationship, int):
            consent_id = relationship

        if not consent_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "No consent context provided for cross-role access",
            )

        consent = self._db.query(Consent).filter(Consent.id == consent_id).first()
        if not consent:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent not found",
            )

        # The consent must belong to the patient whose data is being accessed.
        if consent.patient_id != ctx.patient_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is not bound to the requested patient",
            )

        # A doctor-specific consent can only authorize that doctor.
        if consent.doctor_id is not None and consent.doctor_id != ctx.actor.id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is not bound to the requesting doctor",
            )

        # A hospital-specific consent requires an explicit matching hospital context.
        if consent.hospital_id is not None and consent.hospital_id != ctx.hospital_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is not bound to the requesting hospital",
            )

        # Relationship objects must not contradict the consent itself.
        for field in ("patient_id", "doctor_id", "hospital_id"):
            relationship_value = getattr(relationship, field, None)
            consent_value = getattr(consent, field, None)
            if relationship_value is not None and consent_value is not None and relationship_value != consent_value:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    f"Consent relationship mismatch: {field}",
                )

        authoritative_state = self._db.query(ConsentState).filter(
            ConsentState.consent_id == consent.id
        ).order_by(ConsentState.created_at.desc(), ConsentState.id.desc()).first()

        if not authoritative_state:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent state history is missing",
            )

        if authoritative_state.status != ConsentStatus.ACTIVE.value:
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                f"Consent is currently {authoritative_state.status}",
            )

        policy = authoritative_state.policy_version
        if not policy:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Policy version not found",
            )

        if purpose:
            allowed_purposes = policy.policy_payload.get("allowed_purposes", [])
            if purpose not in allowed_purposes:
                return AuthorizationDecision.deny(
                    DenialReason.OPERATION_NOT_ALLOWED,
                    f"PURPOSE_NOT_ALLOWED: '{purpose}' is not permitted by the active consent policy",
                )

        allowed_operations = policy.policy_payload.get("allowed_operations", [])
        if allowed_operations and ctx.operation.value not in allowed_operations:
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                f"OPERATION_NOT_ALLOWED: '{ctx.operation.value}' is not permitted by the active consent policy",
            )

        return AuthorizationDecision.allow()
