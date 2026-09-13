"""Versioned privacy retention actions with legal-hold exclusion."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import exists
from sqlalchemy.orm import Session

from app.models.access import DocumentAccessGrant, DocumentAccessRequest
from app.models.auth import RefreshTokenHistory
from app.models.document import MedicalDocument
from app.models.privacy import PrivacyLegalHold


POLICY_VERSION = "2026-09-13.1"


@dataclass
class RetentionResult:
    policy_version: str = POLICY_VERSION
    expired_grants: int = 0
    expired_requests: int = 0
    archived_documents: int = 0
    deleted_refresh_fingerprints: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def apply_retention(
    db: Session,
    *,
    now: datetime | None = None,
    clinical_retention_days: int = 2557,
    refresh_history_days: int = 90,
) -> RetentionResult:
    if clinical_retention_days <= 0 or refresh_history_days <= 0:
        raise ValueError("Retention periods must be positive")
    current_time = now or datetime.now(timezone.utc)
    result = RetentionResult()

    result.expired_grants = db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.status == "active",
        DocumentAccessGrant.expires_at <= current_time,
    ).update({DocumentAccessGrant.status: "expired"}, synchronize_session=False)

    result.expired_requests = db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.status == "pending",
        DocumentAccessRequest.requested_at <= current_time - timedelta(days=30),
    ).update(
        {
            DocumentAccessRequest.status: "expired",
            DocumentAccessRequest.responded_at: current_time,
        },
        synchronize_session=False,
    )

    active_hold = exists().where(
        PrivacyLegalHold.patient_id == MedicalDocument.patient_id,
        PrivacyLegalHold.active.is_(True),
    )
    result.archived_documents = db.query(MedicalDocument).filter(
        MedicalDocument.status == "active",
        MedicalDocument.created_at <= current_time - timedelta(days=clinical_retention_days),
        ~active_hold,
    ).update({MedicalDocument.status: "archived"}, synchronize_session=False)

    result.deleted_refresh_fingerprints = db.query(RefreshTokenHistory).filter(
        RefreshTokenHistory.used_at <= current_time - timedelta(days=refresh_history_days)
    ).delete(synchronize_session=False)
    return result
