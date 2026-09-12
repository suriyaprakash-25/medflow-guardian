"""
MedFlow Guardian — Central Authorization Engine
================================================

The backend is the collocated Policy Decision Point and Policy Enforcement Point.
Authorization defaults to deny, evaluates server-trusted context, and records an
auditable decision before protected operations proceed.
"""

from __future__ import annotations

import enum
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.audit import AuditLog
from app.models.consent import Consent, ConsentState
from app.models.document import MedicalDocument
from app.models.hospital import Appointment, Hospital, HospitalStaff, Visit
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)


class Operation(str, enum.Enum):
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


class ResourceType(str, enum.Enum):
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
    STAFF = "staff"
    USER = "user"
    PATIENT_RECORD = "patient_record"
    APPOINTMENT = "appointment"
    FHIR_EXPORT = "fhir_export"
    CONSENT = "consent"


class DenialReason(str, enum.Enum):
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
    AUDIT_PERSISTENCE_FAILED = "audit_persistence_failed"
    CONSENT_REQUIRED = "consent_required"
    ENFORCEMENT_STATE_INVALID = "enforcement_state_invalid"
    ENFORCEMENT_STATE_STALE = "enforcement_state_stale"


@dataclass
class AuthorizationContext:
    actor: User
    operation: Operation
    resource_type: ResourceType
    db: Session
    resource: Optional[Any] = None
    hospital_id: Optional[int] = None
    patient_id: Optional[int] = None
    relationship_context: Optional[Any] = None
    purpose: Optional[str] = None
    consent_id: Optional[int] = None
    consent_state_id: Optional[int] = None
    policy_version: Optional[int] = None
    requires_consent: Optional[bool] = None


@dataclass
class AuthorizationDecision:
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
            detail="No authorization rule matched — default deny applies",
        )


class AuthorizationAuditError(RuntimeError):
    """Raised when a mandatory CAE audit row cannot be persisted safely."""


class AuthorizationService:
    def __init__(self, db: Session):
        self._db = db

    def authorize(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        if ctx.actor is None:
            return AuthorizationDecision.deny(
                DenialReason.AUTHENTICATION_REQUIRED,
                "No authenticated actor",
            )
        if not ctx.actor.is_active:
            return AuthorizationDecision.deny(
                DenialReason.USER_INACTIVE,
                "User account is inactive",
            )

        try:
            result = self._dispatch(ctx)
            if result.allowed:
                from app.services.consent import ConsentService

                consent_decision = ConsentService(self._db).evaluate(
                    ctx=ctx,
                    purpose=ctx.purpose,
                )
                if not consent_decision.allowed:
                    result = consent_decision
        except Exception:
            result = AuthorizationDecision.default_deny()

        try:
            self._audit_decision(ctx, result)
        except AuthorizationAuditError:
            if result.allowed:
                return AuthorizationDecision.deny(
                    DenialReason.AUDIT_PERSISTENCE_FAILED,
                    "Authorization audit unavailable; operation denied",
                )

        return result

    def _audit_decision(self, ctx: AuthorizationContext, decision: AuthorizationDecision):
        """Persist authorization evidence without weakening fail-closed behavior.

        Successful LIST decisions are security-relevant disclosures and are no
        longer skipped. In production request sessions they are committed before
        the list is released so a read cannot succeed with only transient audit
        evidence. Test SAVEPOINT sessions retain their existing transaction model.
        """
        if not isinstance(self._db, Session):
            return

        resource_id_str = str(getattr(ctx.resource, "id", "")) if ctx.resource else None

        consent_id = ctx.consent_id
        if consent_id is None and ctx.relationship_context:
            consent_id = (
                ctx.relationship_context
                if isinstance(ctx.relationship_context, int)
                else getattr(ctx.relationship_context, "consent_id", None)
            )

        attempted_ids = {}

        def existing_id(model, value, label):
            if value is None:
                return None
            with self._db.no_autoflush:
                exists = self._db.query(model.id).filter(model.id == value).first()
            if not exists:
                attempted_ids[label] = value
                return None
            return value

        organization_id = existing_id(Hospital, ctx.hospital_id, "attempted_organization_id")
        patient_id = existing_id(User, ctx.patient_id, "attempted_patient_id")
        audit_consent_id = existing_id(Consent, consent_id, "attempted_consent_id")
        audit_consent_state_id = existing_id(
            ConsentState,
            ctx.consent_state_id,
            "attempted_consent_state_id",
        )

        metadata = {}
        if decision.detail:
            metadata["detail"] = decision.detail
        if ctx.operation == Operation.LIST:
            metadata["list_access"] = True
        metadata.update(attempted_ids)

        log = AuditLog(
            actor_id=ctx.actor.id,
            actor_role=ctx.actor.role,
            organization_id=organization_id,
            patient_id=patient_id,
            operation=ctx.operation.value,
            resource_type=ctx.resource_type.value,
            resource_id=resource_id_str,
            purpose=ctx.purpose,
            consent_id=audit_consent_id,
            consent_state_id=audit_consent_state_id,
            policy_version=ctx.policy_version,
            decision="ALLOW" if decision.allowed else "DENY",
            denial_reason=decision.reason.value if decision.reason else None,
            metadata_json=json.dumps(metadata) if metadata else None,
        )

        durable_list_allow = ctx.operation == Operation.LIST and decision.allowed

        try:
            if self._db.in_nested_transaction():
                self._db.add(log)
                self._db.flush()
            else:
                with self._db.begin_nested():
                    self._db.add(log)
                    self._db.flush()
                if durable_list_allow:
                    self._db.commit()
        except Exception as exc:
            try:
                self._db.rollback()
            except Exception:
                logger.exception("Authorization audit rollback failed")
            logger.exception(
                "Authorization audit persistence failed for actor=%s operation=%s resource_type=%s",
                getattr(ctx.actor, "id", None),
                ctx.operation.value,
                ctx.resource_type.value,
            )
            raise AuthorizationAuditError("Authorization audit persistence failed") from exc

    def _dispatch(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        if ctx.resource_type == ResourceType.DOCUMENT:
            return self._authorize_document(ctx)
        if ctx.resource_type == ResourceType.ACCESS_REQUEST:
            return self._authorize_access_request(ctx)
        if ctx.resource_type == ResourceType.ACCESS_GRANT:
            return self._authorize_access_grant(ctx)
        if ctx.resource_type == ResourceType.TRIAGE_REQUEST:
            return self._authorize_triage(ctx)
        if ctx.resource_type == ResourceType.VISIT:
            return self._authorize_visit(ctx)
        if ctx.resource_type == ResourceType.NOTIFICATION:
            return self._authorize_notification(ctx)
        if ctx.resource_type == ResourceType.AUDIT_LOG:
            return self._authorize_audit_log(ctx)
        if ctx.resource_type == ResourceType.PATIENT_READING:
            return self._authorize_patient_reading(ctx)
        if ctx.resource_type == ResourceType.MESSAGE:
            return self._authorize_message(ctx)
        if ctx.resource_type == ResourceType.HOSPITAL:
            return self._authorize_hospital(ctx)
        if ctx.resource_type in (
            ResourceType.PRACTITIONER_PROFILE,
            ResourceType.PATIENT_PROFILE,
        ):
            return self._authorize_profile(ctx)
        if ctx.resource_type == ResourceType.STAFF:
            return self._authorize_staff(ctx)
        if ctx.resource_type == ResourceType.USER:
            return self._authorize_user(ctx)
        if ctx.resource_type == ResourceType.PATIENT_RECORD:
            return self._authorize_patient_record(ctx)
        if ctx.resource_type == ResourceType.APPOINTMENT:
            return self._authorize_appointment(ctx)
        if ctx.resource_type == ResourceType.FHIR_EXPORT:
            return self._authorize_fhir_export(ctx)
        if ctx.resource_type == ResourceType.CONSENT:
            return self._authorize_consent(ctx)
        return AuthorizationDecision.default_deny()

    def _get_active_membership(self, user_id: int, hospital_id: int) -> Optional[HospitalStaff]:
        return (
            self._db.query(HospitalStaff)
            .filter(
                HospitalStaff.user_id == user_id,
                HospitalStaff.hospital_id == hospital_id,
                HospitalStaff.is_active == True,
            )
            .first()
        )

    def _require_active_membership(
        self,
        user_id: int,
        hospital_id: int,
    ) -> Optional[AuthorizationDecision]:
        if not hospital_id:
            return AuthorizationDecision.deny(
                DenialReason.INVALID_CONTEXT,
                "No hospital_id in context",
            )
        membership = self._get_active_membership(user_id, hospital_id)
        if not membership:
            return AuthorizationDecision.deny(
                DenialReason.MEMBERSHIP_REQUIRED,
                "No active membership for this organization",
            )
        return None

    def _has_visit_relationship(
        self,
        patient_id: int,
        doctor_id: int,
        hospital_id: Optional[int] = None,
    ) -> bool:
        query = self._db.query(Visit).filter(
            Visit.patient_id == patient_id,
            Visit.doctor_id == doctor_id,
        )
        if hospital_id is not None:
            query = query.filter(Visit.hospital_id == hospital_id)
        return query.first() is not None

    def _get_active_grant(
        self,
        doctor_id: int,
        document_id: int,
    ) -> Optional[DocumentAccessGrant]:
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

    def _authorize_document(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        doc: Optional[MedicalDocument] = (
            ctx.resource if isinstance(ctx.resource, MedicalDocument) else None
        )

        if op == Operation.CREATE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only practitioners may upload documents",
                )
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Missing hospital_id",
                )
            visit = ctx.resource if isinstance(ctx.resource, Visit) else None
            if visit is None:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Document upload requires the authoritative visit context",
                )
            if visit.hospital_id != ctx.hospital_id:
                return AuthorizationDecision.deny(
                    DenialReason.ORGANIZATION_MISMATCH,
                    "Visit hospital does not match upload context",
                )
            if visit.doctor_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RELATIONSHIP_REQUIRED,
                    "Practitioner is not assigned to this visit",
                )
            if ctx.patient_id is not None and visit.patient_id != ctx.patient_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Visit patient does not match upload context",
                )
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        if op == Operation.LIST:
            if actor.role == "patient":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(
                DenialReason.ROLE_NOT_PERMITTED,
                "List not permitted for this role",
            )

        if op == Operation.READ:
            if actor.role == "patient":
                if doc and doc.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Not your document",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if not doc:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_FOUND,
                        "Document not found",
                    )
                if not self._has_visit_relationship(doc.patient_id, actor.id):
                    return AuthorizationDecision.deny(
                        DenialReason.RELATIONSHIP_REQUIRED,
                        "No visit relationship with patient",
                    )
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.DOWNLOAD:
            if not doc:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Document not found",
                )
            if actor.role == "patient":
                if doc.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Not your document",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                membership = self._get_active_membership(actor.id, doc.hospital_id)
                uploader = doc.uploaded_by_doctor_id == actor.id
                grant = self._get_active_grant(actor.id, doc.id)
                if membership or uploader or grant:
                    if grant and not (membership or uploader):
                        ctx.relationship_context = grant
                    return AuthorizationDecision.allow()
                return AuthorizationDecision.deny(
                    DenialReason.ORGANIZATION_MISMATCH,
                    "Not authorized: no membership, upload relationship, or active grant",
                )
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    def _authorize_patient_record(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op == Operation.CREATE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only doctors can create patient records",
                )
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.LIST):
            if actor.role == "patient":
                if ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Not your record",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if ctx.hospital_id:
                    membership = self._get_active_membership(actor.id, ctx.hospital_id)
                    if membership:
                        return AuthorizationDecision.allow()
                if ctx.relationship_context:
                    return AuthorizationDecision.allow()
                return AuthorizationDecision.deny(
                    DenialReason.ORGANIZATION_MISMATCH,
                    "Not authorized: no membership or active grant context",
                )
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.UPDATE:
            if actor.role == "doctor":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    def _authorize_appointment(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        appointment = ctx.resource if isinstance(ctx.resource, Appointment) else None

        if op == Operation.CREATE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only patients create appointments",
                )
            if ctx.patient_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Patients may only create their own appointments",
                )
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.LIST):
            if actor.role == "patient":
                if ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Not your appointment",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if ctx.relationship_context is not None and ctx.relationship_context != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "A practitioner may only list their own appointments",
                    )
                if ctx.hospital_id:
                    denial = self._require_active_membership(actor.id, ctx.hospital_id)
                    if denial:
                        return denial
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.UPDATE:
            if appointment is None:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Appointment update requires authoritative appointment context",
                )
            if actor.role == "patient":
                if appointment.patient_id != actor.id or ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Not your appointment",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if appointment.doctor_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Practitioner is not assigned to this appointment",
                    )
                if appointment.hospital_id != ctx.hospital_id:
                    return AuthorizationDecision.deny(
                        DenialReason.ORGANIZATION_MISMATCH,
                        "Appointment hospital does not match authorization context",
                    )
                denial = self._require_active_membership(actor.id, appointment.hospital_id)
                if denial:
                    return denial
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    def _authorize_fhir_export(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        if ctx.operation != Operation.READ:
            return AuthorizationDecision.default_deny()
        if actor.role == "patient":
            if ctx.patient_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Cannot export other patient records",
                )
            return AuthorizationDecision.allow()
        if actor.role == "doctor":
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
                membership_denial = self._require_active_membership(
                    actor.id,
                    consent.hospital_id,
                )
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
        if ctx.resource is not None and ctx.resource.patient_id != ctx.actor.id:
            return AuthorizationDecision.deny(
                DenialReason.RESOURCE_NOT_OWNED,
                "Not your consent",
            )
        return AuthorizationDecision.allow()

    def _authorize_access_request(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        req: Optional[DocumentAccessRequest] = ctx.resource

        if op == Operation.REQUEST_ACCESS:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only practitioners may request access",
                )
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Missing hospital_id",
                )
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        if op == Operation.LIST:
            if actor.role in ("doctor", "patient"):
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.GRANT_ACCESS:
            if actor.role != "patient":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only patients may approve access requests",
                )
            if not req:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Access request not found",
                )
            if req.patient_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Not your access request",
                )
            if req.status != "pending":
                return AuthorizationDecision.deny(
                    DenialReason.OPERATION_NOT_ALLOWED,
                    f"Request is already {req.status}",
                )
            return AuthorizationDecision.allow()

        if op == Operation.DELETE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")
            if not req:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Access request not found",
                )
            if req.patient_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Not your access request",
                )
            if req.status != "pending":
                return AuthorizationDecision.deny(
                    DenialReason.OPERATION_NOT_ALLOWED,
                    f"Request is already {req.status}",
                )
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

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
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only patients may revoke grants",
                )
            if not grant:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Grant not found",
                )
            if grant.patient_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Not your grant",
                )
            if grant.status != "active":
                return AuthorizationDecision.deny(
                    DenialReason.OPERATION_NOT_ALLOWED,
                    "Grant is not active",
                )
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    def _authorize_triage(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        triage = ctx.resource

        if op == Operation.CREATE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only patients may submit triage requests",
                )
            return AuthorizationDecision.allow()

        if op == Operation.LIST:
            if actor.role in ("patient", "doctor"):
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.UPDATE_STATUS:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only practitioners may update triage status",
                )
            if not triage:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Triage request not found",
                )
            denial = self._require_active_membership(actor.id, triage.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    def _authorize_visit(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        visit: Optional[Visit] = ctx.resource

        if op == Operation.CREATE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only practitioners may create visits",
                )
            if not ctx.patient_id or not ctx.hospital_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Visit creation requires patient and hospital context",
                )
            if ctx.relationship_context != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Practitioner may only create visits assigned to themselves",
                )
            denial = self._require_active_membership(actor.id, ctx.hospital_id)
            if denial:
                return denial
            return AuthorizationDecision.allow()

        if op == Operation.LIST:
            if actor.role == "patient":
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        if op == Operation.READ:
            if not visit:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Visit not found",
                )
            if actor.role == "patient":
                if visit.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Not your visit",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                membership = self._get_active_membership(actor.id, visit.hospital_id)
                if not membership and visit.doctor_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.ORGANIZATION_MISMATCH,
                        "No membership for this visit's hospital",
                    )
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    def _authorize_notification(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation
        notif: Optional[Notification] = ctx.resource

        if op == Operation.LIST:
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.MARK_READ):
            if op == Operation.MARK_READ and notif is None and ctx.relationship_context == actor.id:
                return AuthorizationDecision.allow()
            if not notif:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_FOUND,
                    "Notification not found",
                )
            if notif.user_id != actor.id:
                return AuthorizationDecision.deny(
                    DenialReason.RESOURCE_NOT_OWNED,
                    "Not your notification",
                )
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    def _authorize_audit_log(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op == Operation.LIST:
            if actor.role in ("patient", "doctor", "platform_admin"):
                return AuthorizationDecision.allow()
            if ctx.hospital_id:
                membership = self._get_active_membership(actor.id, ctx.hospital_id)
                if membership and membership.role == "admin":
                    return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    def _authorize_patient_reading(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op == Operation.CREATE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only patients may submit readings",
                )
            return AuthorizationDecision.allow()

        if op in (Operation.READ, Operation.LIST):
            if actor.role == "patient":
                if ctx.patient_id is not None and ctx.patient_id != actor.id:
                    return AuthorizationDecision.deny(
                        DenialReason.RESOURCE_NOT_OWNED,
                        "Cannot read another patient's readings",
                    )
                return AuthorizationDecision.allow()
            if actor.role == "doctor":
                if ctx.relationship_context:
                    return AuthorizationDecision.allow()
                if ctx.patient_id:
                    if not self._has_visit_relationship(ctx.patient_id, actor.id):
                        return AuthorizationDecision.deny(
                            DenialReason.RELATIONSHIP_REQUIRED,
                            "No visit relationship with patient",
                        )
                    return AuthorizationDecision.allow()
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "patient_id required",
                )
            return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")

        return AuthorizationDecision.default_deny()

    def _authorize_message(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if op in (Operation.CREATE, Operation.LIST):
            other_user_id = ctx.relationship_context
            if not other_user_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Other user ID required in relationship_context",
                )
            if actor.role == "patient":
                patient_id = actor.id
                doctor_id = other_user_id
            elif actor.role == "doctor":
                patient_id = other_user_id
                doctor_id = actor.id
            else:
                return AuthorizationDecision.deny(DenialReason.ROLE_NOT_PERMITTED, "")
            if not self._has_visit_relationship(patient_id, doctor_id):
                return AuthorizationDecision.deny(
                    DenialReason.RELATIONSHIP_REQUIRED,
                    "No visit relationship",
                )
            return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    def _authorize_hospital(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if actor.role == "platform_admin":
            return AuthorizationDecision.allow()

        if op in (Operation.LIST, Operation.READ):
            return AuthorizationDecision.allow()

        if op == Operation.UPDATE:
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Missing hospital_id",
                )
            membership = self._get_active_membership(actor.id, ctx.hospital_id)
            if membership and membership.role == "admin":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(
                DenialReason.ROLE_NOT_PERMITTED,
                "Only organization administrators can update hospital details",
            )

        return AuthorizationDecision.default_deny()

    def _authorize_profile(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if ctx.resource_type == ResourceType.PRACTITIONER_PROFILE:
            if actor.role != "doctor":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only practitioners have practitioner profiles",
                )
            if op in (Operation.READ, Operation.CREATE, Operation.UPDATE):
                return AuthorizationDecision.allow()

        if ctx.resource_type == ResourceType.PATIENT_PROFILE:
            if actor.role != "patient":
                return AuthorizationDecision.deny(
                    DenialReason.ROLE_NOT_PERMITTED,
                    "Only patients have patient profiles",
                )
            if op in (Operation.READ, Operation.UPDATE):
                return AuthorizationDecision.allow()

        return AuthorizationDecision.default_deny()

    def _authorize_staff(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if actor.role == "platform_admin":
            return AuthorizationDecision.allow()

        if op in (Operation.LIST, Operation.MANAGE_STAFF):
            if not ctx.hospital_id:
                return AuthorizationDecision.deny(
                    DenialReason.INVALID_CONTEXT,
                    "Missing hospital_id",
                )
            membership = self._get_active_membership(actor.id, ctx.hospital_id)
            if membership and membership.role == "admin":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(
                DenialReason.ROLE_NOT_PERMITTED,
                "Only organization administrators can manage staff",
            )

        return AuthorizationDecision.default_deny()

    def _authorize_user(self, ctx: AuthorizationContext) -> AuthorizationDecision:
        actor = ctx.actor
        op = ctx.operation

        if actor.role == "platform_admin":
            return AuthorizationDecision.allow()

        if op in (Operation.LIST, Operation.READ):
            if actor.role == "doctor":
                return AuthorizationDecision.allow()
            return AuthorizationDecision.deny(
                DenialReason.ROLE_NOT_PERMITTED,
                "Only administrators can manage users",
            )

        return AuthorizationDecision.default_deny()
