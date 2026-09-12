from typing import Optional

from sqlalchemy.orm import Session

from app.models.consent import Consent, ConsentState, ConsentStatus
from app.services.authorization import AuthorizationContext, AuthorizationDecision, DenialReason


class ConsentService:
    """Evaluate patient-consent policy inside the collocated Model A boundary.

    The backend is both PDP and PEP. The caller may supply request context such
    as purpose, but authorization state is resolved server-side from the
    authoritative consent, latest ConsentState, and referenced policy version.
    """

    def __init__(self, db: Session):
        self._db = db

    def evaluate(
        self,
        ctx: AuthorizationContext,
        purpose: Optional[str],
    ) -> AuthorizationDecision:
        """Evaluate consent state, purpose, and operation for patient-bound access.

        Patient self-access does not require a consent policy. Operations with no
        patient subject are outside consent evaluation. Every other patient-bound
        request is cross-role/governed access and therefore requires an explicit
        consent context and a non-blank purpose before policy evaluation can ALLOW.
        """
        # 1. Patient self-access is not a third-party disclosure and therefore
        # does not require a consent policy or a purpose supplied for another
        # party's use of the data.
        if ctx.actor.role == "patient" and ctx.patient_id == ctx.actor.id:
            return AuthorizationDecision.allow()

        if ctx.requires_consent is False:
            return AuthorizationDecision.allow()

        # If there is no patient subject in the trusted authorization context,
        # consent does not apply (for example, listing hospitals).
        if not ctx.patient_id:
            return AuthorizationDecision.allow()

        # 2. Extract explicit consent context. New routes use ctx.consent_id;
        # relationship_context remains supported for existing access-grant paths.
        consent_id = ctx.consent_id
        if not consent_id:
            consent_id = getattr(ctx.relationship_context, "consent_id", None)
        if not consent_id and isinstance(ctx.relationship_context, int):
            consent_id = ctx.relationship_context

        if not consent_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "No consent context provided for cross-role access",
            )

        # 3. Bind the supplied consent to the exact patient, practitioner, and
        # organization in the trusted authorization context. A valid consent ID
        # for another subject must never authorize this request.
        consent = self._db.query(Consent).filter(Consent.id == consent_id).first()
        if not consent:
            return AuthorizationDecision.deny(
                DenialReason.CONSENT_REQUIRED,
                "Consent context was not found",
            )
        if consent.patient_id != ctx.patient_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is bound to another patient",
            )
        if consent.doctor_id is not None and (
            ctx.actor.role != "doctor" or consent.doctor_id != ctx.actor.id
        ):
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is bound to another doctor/practitioner",
            )
        if consent.hospital_id is not None and consent.hospital_id != ctx.hospital_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent is bound to another hospital/organization",
            )

        # 4. Load the authoritative latest state. No client-supplied enforcement
        # snapshot participates in the current collocated PDP+PEP architecture.
        authoritative_state = (
            self._db.query(ConsentState)
            .filter(ConsentState.consent_id == consent_id)
            .order_by(ConsentState.created_at.desc(), ConsentState.id.desc())
            .first()
        )
        if not authoritative_state:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Consent state history is missing",
            )

        # Populate the governance snapshot before lifecycle/policy denial so
        # both ALLOW and DENY audit rows can explain the authoritative state used.
        policy = authoritative_state.policy_version
        ctx.consent_id = consent_id
        ctx.consent_state_id = authoritative_state.id
        ctx.policy_version = getattr(policy, "version_number", None)

        # 5. Only the latest ACTIVE state can authorize a disclosure.
        if authoritative_state.status != ConsentStatus.ACTIVE.value:
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                f"Consent is currently {authoritative_state.status}",
            )

        # 6. The authoritative state must resolve to a policy version.
        if not policy:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "Policy version not found",
            )

        # 7. RIGHT PURPOSE is mandatory for governed cross-role patient access.
        # Missing, empty, or whitespace-only purpose must never skip the policy
        # check. Purpose tokens are intentionally matched exactly; this service
        # does not silently rewrite/normalize semantic values.
        if not isinstance(purpose, str) or not purpose.strip():
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "PURPOSE_REQUIRED: explicit purpose is required for cross-role patient access",
            )

        allowed_purposes = policy.policy_payload.get("allowed_purposes", [])
        if purpose not in allowed_purposes:
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                f"PURPOSE_NOT_ALLOWED: '{purpose}' is not permitted by the active consent policy",
            )

        # 8. Operation must also be granted by the active policy. Preserve the
        # existing empty-list semantics for now; policy-shape hardening is a
        # separate concern and should not be silently changed in this phase.
        allowed_operations = policy.policy_payload.get("allowed_operations", [])
        if allowed_operations and ctx.operation.value not in allowed_operations:
            return AuthorizationDecision.deny(
                DenialReason.OPERATION_NOT_ALLOWED,
                f"OPERATION_NOT_ALLOWED: '{ctx.operation.value}' is not permitted by the active consent policy",
            )

        return AuthorizationDecision.allow()
