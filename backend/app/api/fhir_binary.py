import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_authorization_service, get_current_user
from app.core.database import get_db
from app.models.audit import AuditLog
from app.models.document import MedicalDocument
from app.models.user import User
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.consent_context import resolve_active_document_grant
from app.services.interoperability.fhir_binary import to_fhir_binary
from app.services.malware import SCAN_CLEAN, SCAN_ERROR, SCAN_MALICIOUS, SCAN_PENDING
from app.services.storage import storage_service


logger = logging.getLogger(__name__)
router = APIRouter()


def _binary_release_audit(
    *,
    current_user: User,
    document: MedicalDocument,
    allowed: bool,
    purpose: Optional[str] = None,
    consent_id: Optional[int] = None,
    denial_reason: Optional[str] = None,
) -> AuditLog:
    """Build the durable release audit required for protected document bytes."""
    return AuditLog(
        actor_id=current_user.id,
        actor_role=current_user.role,
        organization_id=document.hospital_id,
        patient_id=document.patient_id,
        operation="download_release",
        resource_type="document",
        resource_id=str(document.id),
        purpose=purpose,
        consent_id=consent_id,
        enforcement_point="fastapi-fhir-binary-pep",
        decision="ALLOW" if allowed else "DENY",
        denial_reason=denial_reason,
        metadata_json=json.dumps(
            {
                "scan_status": document.scan_status,
                "representation": "fhir_binary",
            }
        ),
    )


def _commit_binary_audit(db: Session, audit: AuditLog) -> None:
    """Fail closed when the security audit cannot be durably persisted."""
    try:
        db.add(audit)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("FHIR Binary security audit persistence failed")
        raise HTTPException(
            status_code=503,
            detail="Security audit is temporarily unavailable; FHIR Binary release denied",
        ) from exc


@router.get("/interoperability/fhir/Binary/{document_id}")
def read_fhir_binary(
    document_id: int,
    purpose: Optional[str] = Query(
        None,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Z][A-Z0-9_]*$",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    """Read one protected document as a FHIR R4 Binary resource."""
    document = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.id == document_id)
        .first()
    )

    trusted_grant = None
    if current_user.role == "doctor" and document is not None:
        if purpose is None:
            raise HTTPException(
                status_code=403,
                detail="PURPOSE_REQUIRED: practitioner FHIR Binary read requires an explicit purpose",
            )
        trusted_grant = resolve_active_document_grant(
            db,
            doctor_id=current_user.id,
            document=document,
        )

    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_user,
            operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=db,
            resource=document,
            hospital_id=document.hospital_id if document else None,
            patient_id=document.patient_id if document else None,
            purpose=purpose,
            consent_id=(trusted_grant.consent_id if trusted_grant else None),
            relationship_context=trusted_grant,
            enforcement_point="fastapi-fhir-binary-pep",
        )
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=404 if decision.detail == "Document not found" else 403,
            detail=decision.detail,
        )

    consent_id = trusted_grant.consent_id if trusted_grant else None
    if document.scan_status != SCAN_CLEAN:
        if document.scan_status == SCAN_MALICIOUS:
            detail = "FHIR Binary blocked: malware detected"
        elif document.scan_status == SCAN_PENDING:
            detail = "FHIR Binary remains quarantined pending malware scan"
        elif document.scan_status == SCAN_ERROR:
            detail = "FHIR Binary remains quarantined because malware scanning failed"
        else:
            detail = "FHIR Binary remains quarantined because scan state is not releasable"
        _commit_binary_audit(
            db,
            _binary_release_audit(
                current_user=current_user,
                document=document,
                allowed=False,
                purpose=purpose,
                consent_id=consent_id,
                denial_reason="malware_quarantine",
            ),
        )
        raise HTTPException(status_code=403, detail=detail)

    try:
        file_bytes = storage_service.download_document(document.stored_filename)
    except HTTPException:
        _commit_binary_audit(
            db,
            _binary_release_audit(
                current_user=current_user,
                document=document,
                allowed=False,
                purpose=purpose,
                consent_id=consent_id,
                denial_reason="storage_unavailable",
            ),
        )
        raise
    except Exception as exc:
        _commit_binary_audit(
            db,
            _binary_release_audit(
                current_user=current_user,
                document=document,
                allowed=False,
                purpose=purpose,
                consent_id=consent_id,
                denial_reason="storage_unavailable",
            ),
        )
        raise HTTPException(
            status_code=503,
            detail="Document storage is temporarily unavailable",
        ) from exc

    _commit_binary_audit(
        db,
        _binary_release_audit(
            current_user=current_user,
            document=document,
            allowed=True,
            purpose=purpose,
            consent_id=consent_id,
        ),
    )
    return JSONResponse(
        to_fhir_binary(document, file_bytes),
        media_type="application/fhir+json",
    )
