"""
MedFlow Guardian — Central Authorization Engine
================================================
Phase 4 Implementation

This module implements the Central Authorization Engine (CAE) for MedFlow Guardian.
It answers the question:

    "Is this authenticated actor permitted to perform this operation
     on this resource in this organization/context?"

Architecture:
    Authentication → Identity → Organization Membership → Organization Context
        → Central Authorization Engine → ALLOW / DENY → Protected Operation

Design Principles:
    1. DEFAULT DENY — If authorization cannot establish permission, DENY.
    2. Separation of concerns — Authentication ≠ Authorization ≠ Consent (Phase 5).
    3. Explicit, auditable decisions — Every decision carries a typed reason.
    4. Extensible — Phase 5 can add Consent/Policy/Enforcement fields without
       rewriting every router.
    5. No role = full access — Role is ONE input, not the complete authorization model.

Phase 5 Extension Points (DO NOT ACTIVATE YET):
    - AuthorizationContext.purpose
    - AuthorizationContext.consent_state_id
    - AuthorizationContext.policy_version
    - AuthorizationContext.enforcement_state
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Any

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.hospital import HospitalStaff, Hospital, Visit
from app.models.document import MedicalDocument
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.notification import Notification
from app.models.audit import AuditLog


# ---------------------------------------------------------------------------
# Vocabulary — Operations
# ---------------------------------------------------------------------------

class Operation(str, enum.Enum):
    """Centralized vocabulary for protected operations."""
    READ = "read"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    DOWNLOAD = "download"
    REQUEST_ACCESS = "request_access"
    GRANT_ACCESS = "grant_access"
    REVOKE_ACCESS = "revoke_access"
    LIST = "list"
    MARK_READ = "mark_read"
    UPDATE_STATUS = "update_status"
    MANAGE_STAFF = "manage_staff"
    VIEW_AUDIT = "view_audit"
    MANAGE_USERS = "manage_users"
    VIEW_DASHBOARD = "view_dashboard"
    MANAGE_ORGANIZATIONS = "manage_organizations"


# ---------------------------------------------------------------------------
# Vocabulary — Resource Types
# ---------------------------------------------------------------------------

class ResourceType(str, enum.Enum):
    """Centralized vocabulary for protected resource types."""
    DOCUMENT = "document"
    ACCESS_REQUEST = "access_request"
    ACCESS_GRANT = "access_grant"
    TRIAGE_REQUEST = "triage_request"
    VISIT = "visit"
    NOTIFICATION = "notification"
    AUDIT_LOG = "audit_log"
    PATIENT_READING = "patient_reading"
    MESSAGE = "message"
    HOSPITAL = "hospital"
    PRACTITIONER_PROFILE = "practitioner_profile"
    PATIENT_PROFILE = "patient_profile"
    # Admin Resources
    STAFF = "staff"
    USER = "user"
    # Phase 13
    PATIENT_RECORD = "patient_record"
    APPOINTMENT = "appointment"
    FHIR_EXPORT = "fhir_export"
    CONSENT = "consent"


# ---------------------------------------------------------------------------
# Decision — Denial Reasons
# ---------------------------------------------------------------------------

class DenialReason(str, enum.Enum):
    """Typed denial reason for auditability and diagnostics."""
    AUTHENTICATION_REQUIRED = "authentication_required"
    USER_INACTIVE = "user_inactive"
    MEMBERSHIP_REQUIRED = "membership_required"
    MEMBERSHIP_INACTIVE = "membership_inactive"
    ORGANIZATION_MISMATCH = "organization_mismatch"
    RESOURCE_NOT_FOUND = "resource_not_found"
    RESOURCE_NOT_OWNED = "resource_not_owned"
    ROLE_NOT_PERMITTED = "role_not_permitted"
    RELATIONSHIP_REQUIRED = "relationship_required"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"
    INVALID_CONTEXT = "invalid_context"
    # Phase 5
    CONSENT_REQUIRED = "consent_required"
    ENFORCEMENT_STATE_INVALID = "enforcement_state_invalid"
    ENFORCEMENT_STATE_STALE = "enforcement_state_stale"


# ---------------------------------------------------------------------------
# Authorization Context
# ---------------------------------------------------------------------------

@dataclass
class AuthorizationContext:
    """
    Full context for an authorization decision.

    Phase 5 extension fields are present but commented out.
    Do NOT activate them in Phase 4 logic.
    """
    actor: User
    operation: Operation
    resource_type: ResourceType
    db: Session

    # Optional: the resource being operated on (can be None for list operations)
    resource: Optional[Any] = None

    # Optional: the organization context (hospital)
    hospital_id: Optional[int] = None

    # Optional: the patient subject (for cross-role operations)
    patient_id: Optional[int] = None

    # Optional: extra relationship data (e.g., active grant, visit)
    relationship_context: Optional[Any] = None

    # ---- Phase 5 Extension Points ----
    purpose: Optional[str] = None
    consent_id: Optional[int] = None
    consent_state_id: Optional[int] = None
    policy_version: Optional[int] = None


# ---------------------------------------------------------------------------
# Authorization Decision
# ---------------------------------------------------------------------------

@dataclass
class AuthorizationDecision:
    """
    Explicit authorization decision with typed reason.
    """
    allowed: bool
    reason: Optional[DenialReason] = None
    detail: str = ""

    @classmethod
    def allow(cls) -> "AuthorizationDecision":
        return cls(allowed=True, reason=None, detail="")

    @classmethod
    def deny(cls, reason: DenialReason, detail: str = "") -> "AuthorizationDecision":
        return cls(allowed=False, reason=reason, detail=detail)

    @classmethod
    def default_deny(cls) -> "AuthorizationDecision":
        return cls(
            allowed=False,
            reason=DenialReason.OPERATION_NOT_ALLOWED,
            detail="No authorization rule matched — default deny applies"
        )


# ---------------------------------------------------------------------------
# Central Authorization Service
# ---------------------------------------------------------------------------

class AuthorizationService:
    """
    Central Authorization Engine for MedFlow Guardian.

    Usage:
        svc = AuthorizationService(db)
        decision = svc.authorize(ctx)
        if not decision.allowed:
            raise HTTPException(403, detail=decision.detail)

    The engine answers:
        "Is this authenticated actor permitted to perform
         this operation on this resource in this context?"

    It does NOT answer consent questions (Phase 5).
    """

    def __init__(self, db: Session):
        self._db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def authorize(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        """
        Evaluate authorization. DEFAULT DENY if no rule matches.
        """
        # Guard: actor must be present (Authentication is a precondition)
        if ctx.actor is None:
            return AuthorizationDecision.deny(
                DenialReason.AUTHENTICATION_REQUIRED,
                "No authenticated actor"
            )

        # Guard: actor must be active
        if not ctx.actor.is_active:
            return AuthorizationDecision.deny(
                DenialReason.USER_INACTIVE,
                "User account is inactive"
            )

        # Route to appropriate rule evaluator
        try:
            result = self._dispatch(ctx)
            
            # PHASE 5: Consent Evaluation (if base authorization passed)
            if result.allowed:
                from app.services.consent import ConsentService
                consent_svc = ConsentService(self._db)
                consent_decision = consent_svc.evaluate(
                    ctx=ctx,
                    purpose=ctx.purpose
                )
                if not consent_decision.allowed:
                    result = consent_decision

        except Exception as e:
            # Never allow on error — fail closed
            result = AuthorizationDecision.default_deny()

        self._audit_decision(ctx, result)
        return result

    def _audit_decision(self, ctx: AuthorizationContext, decision: AuthorizationDecision):
        """Append-only audit logging for security decisions."""
        # Only log document-related decisions, access grants, or explicit denials
        # to avoid flooding the audit log with list operations
        if ctx.operation == Operation.LIST and decision.allowed:
            return
            
        try:
            resource_id_str = str(getattr(ctx.resource, "id", "")) if ctx.resource else None
            
            consent_id = ctx.consent_id
            if consent_id is None and ctx.relationship_context:
                consent_id = (
                    ctx.relationship_context
                    if isinstance(ctx.relationship_context, int)
                    else getattr(ctx.relationship_context, "consent_id", None)
                )
            
            log = AuditLog(
                actor_id=ctx.actor.id,
                actor_role=ctx.actor.role,
                organization_id=ctx.hospital_id,
                patient_id=ctx.patient_id,
                operation=ctx.operation.value,
                resource_type=ctx.resource_type.value,
                resource_id=resource_id_str,
                purpose=ctx.purpose,
                consent_id=consent_id,
                consent_state_id=ctx.consent_state_id,
                policy_version=ctx.policy_version,
                decision="ALLOW" if decision.allowed else "DENY",
                denial_reason=decision.reason.value if decision.reason else None,
                metadata_json=f'{{"detail": "{decision.detail}"}}' if decision.detail else None
            )
            self._db.add(log)
            # Flush immediately to ensure the audit log is written, but let the caller commit the transaction
            self._db.flush()
        except Exception as e:
            print(f"Audit log failed to write: {e}")
            pass

    # ------------------------------------------------------------------
    # Internal Dispatch — DEFAULT DENY
    # ------------------------------------------------------------------

    def _dispatch(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        if ctx.resource_type == ResourceType.DOCUMENT:
            return self._authorize_document(ctx)
        elif ctx.resource_type == ResourceType.ACCESS_REQUEST:
            return self._authorize_access_request(ctx)
        elif ctx.resource_type == ResourceType.ACCESS_GRANT:
            return self._authorize_access_grant(ctx)
        elif ctx.resource_type == ResourceType.TRIAGE_REQUEST:
            return self._authorize_triage(ctx)
        elif ctx.resource_type == ResourceType.VISIT:
            return self._authorize_visit(ctx)
        elif ctx.resource_type == ResourceType.NOTIFICATION:
            return self._authorize_notification(ctx)
        elif ctx.resource_type == ResourceType.AUDIT_LOG:
            return self._authorize_audit_log(ctx)
        elif ctx.resource_type == ResourceType.PATIENT_READING:
            return self._authorize_patient_reading(ctx)
        elif ctx.resource_type == ResourceType.MESSAGE:
            return self._authorize_message(ctx)
        elif ctx.resource_type == ResourceType.HOSPITAL:
            return self._authorize_hospital(ctx)
        elif ctx.resource_type in (ResourceType.PRACTITIONER_PROFILE, ResourceType.PATIENT_PROFILE):
            return self._authorize_profile(ctx)
        elif ctx.resource_type == ResourceType.STAFF:
            return self._authorize_staff(ctx)
        elif ctx.resource_type == ResourceType.USER:
            return self._authorize_user(ctx)
        elif ctx.resource_type == ResourceType.PATIENT_RECORD:
            return self._authorize_patient_record(ctx)
        elif ctx.resource_type == ResourceType.APPOINTMENT:
            return self._authorize_appointment(ctx)
        elif ctx.resource_type == ResourceType.FHIR_EXPORT:
            return self._authorize_fhir_export(ctx)
        elif ctx.resource_type == ResourceType.CONSENT:
            return self._authorize_consent(ctx)
        else:
            return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Helpers — Organization Membership
    # ------------------------------------------------------------------

    def _get_active_membership(self, user_id: int, hospital_id: int) -> Optional[HospitalStaff]:
        """Return active HospitalStaff row or None. Never trust client-supplied IDs."""
        return self._db.query(HospitalStaff).filter(
            HospitalStaff.user_id == user_id,
            HospitalStaff.hospital_id == hospital_id,
            HospitalStaff.is_active == True
        ).first()

    def _require_active_membership(
        self, user_id: int, hospital_id: int
    ) -> Optional[AuthorizationDecision]:
        """
        Return a denial decision if user has no active membership,
        else return None (meaning check passed).
        """
        if not hospital_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT, "No hospital_id in context"
            )
        membership = self._get_active_membership(user_id, hospital_id)
        if not membership:
            return AuthorizationDecision.deny(
                DenialReason.MEMBERSHIP_REQUIRED,
                "No active membership for this organization"
            )
        return None  # passed

    def _has_visit_relationship(
        self,
        patient_id: int,
        doctor_id: int,
        hospital_id: Optional[int] = None,
    ) -> bool:
        """Check if a visit relationship exists between patient and doctor."""
        query = self._db.query(Visit).filter(
            Visit.patient_id == patient_id,
            Visit.doctor_id == doctor_id,
        )
        if hospital_id is not None:
            query = query.filter(Visit.hospital_id == hospital_id)
        return query.first() is not None

    def _get_active_grant(self, doctor_id: int, document_id: int) -> Optional[DocumentAccessGrant]:
        """Return a matching non-expired active grant for this exact document.

        A practitioner can have several simultaneous grants. Inspecting only the
        first active grant made authorization depend on database row order and could
        deny a valid later grant. Resolve deterministically across all candidates and
        return only a grant that explicitly contains the requested document.
        """
        grants = (
            self._db.query(DocumentAccessGrant)
            .filter(
                DocumentAccessGrant.doctor_id == doctor_id,
                DocumentAccessGrant.status == "active",
                DocumentAccessGrant.expires_at > datetime.utcnow(),
            )
            .order_by(
                DocumentAccessGrant.granted_at.desc(),
                DocumentAccessGrant.id.desc(),
            )
            .all()
        )
        for grant in grants:
            if any(doc.id == document_id for doc in grant.granted_documents):
                return grant
        return None

    # ------------------------------------------------------------------
    # Rule: DOCUMENT
    # ------------------------------------------------------------------

    def _authorize_document(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        doc: Optional[MedicalDocument] = ctx.resource

        # --- CREATE (upload) ---
        if op == Operation.CREATE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED, "Only practitioners may upload documents"
                )
            # Membership in the target hospital is required
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "Missing hospital_id")
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        # --- LIST (patient's own) ---
        if op == Operation.LIST:
            if actor.role == "patient":
                # Patient lists own documents — ownership enforced by caller via patient_id filter
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "List not permitted for this role")

        # --- READ metadata ---
        if op == Operation.READ:
            if actor.role == "patient":
                if doc and doc.patient_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your document")
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if not doc:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Document not found")
                # Must have visit relationship with patient
                if not self._has_visit_relationship(doc.patient_id, actor.id):
                    return AuthorizationDecision.deny(
                        DenialReason.RELATIONSHIP_REQUIRED, "No visit relationship with patient"
                    )
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        # --- DOWNLOAD ---
        if op == Operation.DOWNLOAD:
            if not doc:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Document not found")
            if actor.role == "patient":
                if doc.patient_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your document")
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                # Affiliation: must be member of document's hospital OR uploader OR have active grant
                membership = self._get_active_membership(actor.id, doc.hospital_id)
                uploader = doc.uploaded_by_doctor_id == actor.id
                grant = self._get_active_grant(actor.id, doc.id)
                if membership or uploader or grant:
                    # If access is via grant, pass the grant to the context for Consent Evaluation
                    if grant and not (membership or uploader):
                        ctx.relationship_context = grant
                    return AuthorizationDecision.allow()
                return AuthorizationDecision.deny(
                    DenialReason.ORGANIZATION_MISMATCH,
                    "Not authorized: no membership, upload relationship, or active grant"
                )
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: PATIENT_RECORD
    # ------------------------------------------------------------------

    def _authorize_patient_record(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        
        if op == Operation.CREATE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only doctors can create patient records")
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.LIST):
            if actor.role == "patient":
                if ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your record")
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if ctx.hospital_id:
                    membership = self._get_active_membership(actor.id, ctx.hospital_id)
                    if membership:
                        return AuthorizationDecision.allow()
                if ctx.relationship_context:
                    return AuthorizationDecision.allow()
                return AuthorizationDecision.deny(DenialReason.ORGANIZATION_MISMATCH, "Not authorized: no membership or active grant context")
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.UPDATE:
            if actor.role == "doctor":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: APPOINTMENT
    # ------------------------------------------------------------------

    def _authorize_appointment(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op == Operation.CREATE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only patients create appointments")
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.LIST):
            if actor.role == "patient":
                if ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your appointment")
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if ctx.hospital_id:
                    denial = self._require_active_membership(actor.id, ctx.hospital_id)
                    if denial: return denial
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.UPDATE:
            if actor.role == "patient":
                if ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your appointment")
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if ctx.hospital_id:
                    denial = self._require_active_membership(actor.id, ctx.hospital_id)
                    if denial: return denial
                return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: FHIR_EXPORT
    # ------------------------------------------------------------------

    def _authorize_fhir_export(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        if ctx.operation != Operation.READ:
            return AuthorizationDecision.default_deny()
        if actor.role == "patient":
            if ctx.patient_id != actor.id:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Cannot export other patient records")
            return AuthorizationDecision.allow()
        if actor.role == "doctor":
            from app.models.consent import Consent

            consent = ctx.relationship_context
            if not isinstance(consent, Consent) or not ctx.consent_id or consent.id != ctx.consent_id:
                return AuthorizationDecision.deny(
                    DenialReason.CONSENT_REQUIRED,
                    "An explicit consent context is required for practitioner FHIR export",
                )
            if consent.patient_id != ctx.patient_id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Consent does not belong to the requested patient",
                )
            if consent.doctor_id is not None and consent.doctor_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RELATIONSHIP_REQUIRED,
                    "Consent is scoped to another practitioner",
                )
            if consent.hospital_id is not None:
                if ctx.hospital_id != consent.hospital_id:
                    return AuthorizationDecision.deny(
                        DenialReason.ORGANIZATION_MISMATCH,
                        "Consent organization does not match the authorization context",
                    )
                membership_denial = self._require_active_membership(actor.id, consent.hospital_id)
                if membership_denial:
                    return membership_denial
            if not self._has_visit_relationship(
                ctx.patient_id,
                actor.id,
                consent.hospital_id,
            ):
                return AuthorizationDecision.deny(
                    DenialReason.RELATIONSHIP_REQUIRED,
                    "No doctor-patient visit relationship exists",
                )
            return AuthorizationDecision.allow()
        return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

    def _authorize_consent(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        """Consent writes are patient-owned and never authorized by role alone."""
        if ctx.operation not in (Operation.CREATE, Operation.UPDATE):
            return AuthorizationDecision.default_deny()
        if ctx.actor.role != "patient":
            return AuthorizationDecision.deny(
                DenialReason.ROLE_NOT_PERMITTED,
                "Only patients may import or update their consent",
            )
        if ctx.patient_id != ctx.actor.id:
            return AuthorizationDecision.deny(
                DenialReason.RESOURCE_NOT_OWNED,
                "A patient may only import consent for their own record",
            )
        return AuthorizationDecision.allow()

    # ------------------------------------------------------------------
    # Rule: ACCESS_REQUEST
    # ------------------------------------------------------------------

    def _authorize_access_request(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        req: Optional[DocumentAccessRequest] = ctx.resource

        if op == Operation.REQUEST_ACCESS:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only practitioners may request access")
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "Missing hospital_id")
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        if op == Operation.LIST:
            if actor.role in ("doctor", "patient"):
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.GRANT_ACCESS:  # patient approving a request
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only patients may approve access requests")
            if not req:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Access request not found")
            if req.patient_id != actor.id:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your access request")
            if req.status != "pending":
                return AuthorizationDecision.deny(DenialReason.OPERATION_NOT_ALLOWED, f"Request is already {req.status}")
            return AuthorizationDecision.allow()

        if op == Operation.DELETE:  # patient rejecting
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")
            if not req:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Access request not found")
            if req.patient_id != actor.id:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your access request")
            if req.status != "pending":
                return AuthorizationDecision.deny(DenialReason.OPERATION_NOT_ALLOWED, f"Request is already {req.status}")
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: ACCESS_GRANT
    # ------------------------------------------------------------------

    def _authorize_access_grant(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        grant: Optional[DocumentAccessGrant] = ctx.resource

        if op == Operation.LIST:
            if actor.role in ("doctor", "patient"):
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.REVOKE_ACCESS:
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only patients may revoke grants")
            if not grant:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Grant not found")
            if grant.patient_id != actor.id:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your grant")
            if grant.status != "active":
                return AuthorizationDecision.deny(DenialReason.OPERATION_NOT_ALLOWED, "Grant is not active")
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: TRIAGE_REQUEST
    # ------------------------------------------------------------------

    def _authorize_triage(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        triage = ctx.resource

        if op == Operation.CREATE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only patients may submit triage requests")
            return AuthorizationDecision.allow()

        if op == Operation.LIST:
            if actor.role == "patient":
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                # Caller must scope list to actor's memberships — allow the call
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.UPDATE_STATUS:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only practitioners may update triage status")
            if not triage:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Triage request not found")
            # Must be active member of the triage's hospital
            denial = self._require_active_membership(actor.id, triage.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: VISIT
    # ------------------------------------------------------------------

    def _authorize_visit(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        visit: Optional[Visit] = ctx.resource

        if op == Operation.LIST:
            if actor.role == "patient":
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.READ:
            if not visit:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Visit not found")
            if actor.role == "patient":
                if visit.patient_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your visit")
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                # Doctor must have membership in visit's hospital OR be assigned to the visit
                membership = self._get_active_membership(actor.id, visit.hospital_id)
                if not membership and visit.doctor_id != actor.id:
                    return AuthorizationDecision.deny(DenialReason.ORGANIZATION_MISMATCH, "No membership for this visit's hospital")
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: NOTIFICATION
    # ------------------------------------------------------------------

    def _authorize_notification(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        notif: Optional[Notification] = ctx.resource

        if op == Operation.LIST:
            return AuthorizationDecision.allow()  # scoped to actor.id by query

        if op in (Operation.READ, Operation.MARK_READ):
            if not notif:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_FOUND, "Notification not found")
            if notif.user_id != actor.id:
                return AuthorizationDecision.deny(DenialReason.RESOURCE_NOT_OWNED, "Not your notification")
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: AUDIT_LOG
    # ------------------------------------------------------------------

    def _authorize_audit_log(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op == Operation.LIST:
            if actor.role == "patient":
                # Patient can list audit logs for their own patient_id — scoped by caller
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                # Doctor can list their own action logs — scoped by caller
                return AuthorizationDecision.allow()
            if actor.role == "platform_admin":
                return AuthorizationDecision.allow()
            
            # Org Admin logic
            if ctx.hospital_id:
                membership = self._get_active_membership(actor.id, ctx.hospital_id)
                if membership and membership.role == "admin":
                    return AuthorizationDecision.allow()
            
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: PATIENT_READING
    # ------------------------------------------------------------------

    def _authorize_patient_reading(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op == Operation.CREATE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only patients may submit readings")
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.LIST):
            if actor.role == "patient":
                if ctx.patient_id is not None and ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED, "Cannot read another patient's readings"
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                # An explicit consent context is sufficient for the base rule;
                # ConsentService validates its bindings and policy afterward.
                if ctx.relationship_context:
                    return AuthorizationDecision.allow()
                if ctx.patient_id:
                    has_rel = self._has_visit_relationship(ctx.patient_id, actor.id)
                    if not has_rel:
                        return AuthorizationDecision.deny(DenialReason.RELATIONSHIP_REQUIRED, "No visit relationship with patient")
                    return AuthorizationDecision.allow()
                return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "patient_id required")
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: MESSAGE
    # ------------------------------------------------------------------

    def _authorize_message(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op in (Operation.CREATE, Operation.LIST):
            # For messages, relationship_context contains the OTHER user ID
            other_user_id = ctx.relationship_context
            if not other_user_id:
                return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "Other user ID required in relationship_context")

            # Determine patient/doctor IDs based on actor role
            if actor.role == "patient":
                patient_id = actor.id
                doctor_id = other_user_id
            elif actor.role == "doctor":
                patient_id = other_user_id
                doctor_id = actor.id
            else:
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

            if not self._has_visit_relationship(patient_id, doctor_id):
                return AuthorizationDecision.deny(DenialReason.RELATIONSHIP_REQUIRED, "No visit relationship")
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: HOSPITAL
    # ------------------------------------------------------------------

    def _authorize_hospital(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if actor.role == "platform_admin":
            return AuthorizationDecision.allow()

        # Listing/reading hospital info is allowed for any authenticated active user
        if op in (Operation.LIST, Operation.READ):
            return AuthorizationDecision.allow()
            
        if op == Operation.UPDATE:
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "Missing hospital_id")
            membership = self._get_active_membership(actor.id, ctx.hospital_id)
            if membership and membership.role == "admin":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only organization administrators can update hospital details")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: PROFILE (Practitioner / Patient)
    # ------------------------------------------------------------------

    def _authorize_profile(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if ctx.resource_type == ResourceType.PRACTITIONER_PROFILE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only practitioners have practitioner profiles")
            if op in (Operation.READ, Operation.CREATE, Operation.UPDATE):
                return AuthorizationDecision.allow()

        if ctx.resource_type == ResourceType.PATIENT_PROFILE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only patients have patient profiles")
            if op in (Operation.READ, Operation.UPDATE):
                return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: STAFF
    # ------------------------------------------------------------------

    def _authorize_staff(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if actor.role == "platform_admin":
            return AuthorizationDecision.allow()

        if op in (Operation.LIST, Operation.MANAGE_STAFF):
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(DenialReason.INVALID_CONTEXT, "Missing hospital_id")
            
            # Must be active admin of the target hospital
            membership = self._get_active_membership(actor.id, ctx.hospital_id)
            if membership and membership.role == "admin":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only organization administrators can manage staff")

        return AuthorizationDecision.default_deny()

    # ------------------------------------------------------------------
    # Rule: USER
    # ------------------------------------------------------------------

    def _authorize_user(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if actor.role == "platform_admin":
            return AuthorizationDecision.allow()

        if op in (Operation.LIST, Operation.READ):
            # Org admins can view users within their organization.
            # Simplified for now: if actor has an active admin membership anywhere, we'll let the API filter the users by org.
            if actor.role == "doctor": # Doctors can act as org admins
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "Only administrators can manage users")

        return AuthorizationDecision.default_deny()
