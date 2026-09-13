"""Legal-hold-aware privacy request execution."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.auth import Session as AuthSession
from app.models.consent import Consent, ConsentState, ConsentStatus
from app.models.monitoring import Message
from app.models.notification import Notification
from app.models.privacy import PrivacyLegalHold, PrivacyRequest
from app.models.user import PatientProfile, User


class PrivacyExecutionError(RuntimeError):
    pass


def execute_approved_deletion(db: Session, request_id: int) -> PrivacyRequest:
    """Pseudonymize identity and revoke access while retaining governed records.

    Healthcare records and immutable authorization evidence are retained until
    the approved jurisdictional schedule permits erasure. This routine removes
    directly identifying account/profile data and makes all access fail closed.
    """
    privacy_request = (
        db.query(PrivacyRequest)
        .filter(PrivacyRequest.id == request_id)
        .with_for_update()
        .first()
    )
    if not privacy_request:
        raise PrivacyExecutionError("Privacy request not found")
    if privacy_request.request_type != "deletion" or privacy_request.status != "approved":
        raise PrivacyExecutionError("Only approved deletion requests can be executed")

    active_hold = (
        db.query(PrivacyLegalHold.id)
        .filter(
            PrivacyLegalHold.patient_id == privacy_request.patient_id,
            PrivacyLegalHold.active.is_(True),
        )
        .with_for_update()
        .first()
    )
    if active_hold:
        raise PrivacyExecutionError("Active legal hold prevents deletion execution")

    patient = (
        db.query(User)
        .filter(User.id == privacy_request.patient_id, User.role == "patient")
        .with_for_update()
        .first()
    )
    if not patient:
        raise PrivacyExecutionError("Patient account not found")

    consents = db.query(Consent).filter(Consent.patient_id == patient.id).all()
    consent_policies = {}
    for consent in consents:
        if consent.status in {ConsentStatus.REVOKED.value, ConsentStatus.CANCELLED.value}:
            continue
        policy = max(consent.policy_versions, key=lambda item: item.version_number, default=None)
        if policy is None:
            raise PrivacyExecutionError("Consent policy history is incomplete")
        consent_policies[consent.id] = policy

    now = datetime.now(timezone.utc)
    db.query(AuthSession).filter(
        AuthSession.user_id == patient.id,
        AuthSession.revoked_at.is_(None),
    ).update({AuthSession.revoked_at: now}, synchronize_session=False)
    db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.patient_id == patient.id,
        DocumentAccessGrant.status == "active",
    ).update(
        {DocumentAccessGrant.status: "revoked", DocumentAccessGrant.revoked_at: now},
        synchronize_session=False,
    )
    db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.patient_id == patient.id,
        DocumentAccessRequest.status == "pending",
    ).update(
        {DocumentAccessRequest.status: "cancelled", DocumentAccessRequest.responded_at: now},
        synchronize_session=False,
    )

    for consent in consents:
        if consent.status in {ConsentStatus.REVOKED.value, ConsentStatus.CANCELLED.value}:
            continue
        policy = consent_policies[consent.id]
        consent.status = ConsentStatus.REVOKED.value
        db.add(
            ConsentState(
                consent_id=consent.id,
                policy_version_id=policy.id,
                status=ConsentStatus.REVOKED.value,
                reason=f"Privacy deletion request {privacy_request.id} executed",
            )
        )

    profile = db.query(PatientProfile).filter(PatientProfile.user_id == patient.id).first()
    if profile:
        profile.date_of_birth = None
        profile.address = None
        profile.emergency_contact_name = None
        profile.emergency_contact_phone = None

    db.query(Message).filter(
        (Message.sender_id == patient.id) | (Message.receiver_id == patient.id)
    ).update({Message.content: "[redacted by approved privacy request]"}, synchronize_session=False)
    db.query(Notification).filter(Notification.user_id == patient.id).update(
        {Notification.message: "[redacted by approved privacy request]"},
        synchronize_session=False,
    )

    patient.email = f"deleted+{patient.id}@invalid.medflow"
    patient.full_name = "Deleted Patient"
    patient.phone_number = None
    patient.hashed_password = get_password_hash(secrets.token_urlsafe(48))
    patient.is_active = False
    privacy_request.status = "completed"
    privacy_request.completed_at = now
    db.flush()
    return privacy_request
