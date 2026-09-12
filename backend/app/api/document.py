import json
import logging
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_authorization_service,
    get_current_user,
    get_patient_identity,
    get_practitioner_identity,
)
from app.api.websockets import manager
from app.core.database import get_db
from app.core.limiter import limiter
from app.models.audit import AuditLog
from app.models.document import DocumentType, MedicalDocument
from app.models.hospital import Visit
from app.models.notification import Notification
from app.models.user import User
from app.schemas.document import DocumentUploadResponse, MedicalDocumentSchema
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)
from app.services.malware import (
    SCAN_CLEAN,
    SCAN_ERROR,
    SCAN_MALICIOUS,
    SCAN_PENDING,
    scan_document,
)
from app.services.consent_context import resolve_active_document_grant
from app.services.storage import storage_service

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _commit_security_audit(db: Session, audit: AuditLog) -> None:
    """Persist an enforcement audit before any protected bytes are released.

    Audit failure is a release failure. This deliberately fails closed instead of
    swallowing the database error and serving PHI without durable evidence.
    """

    try:
        db.add(audit)
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Security audit persistence failed")
        raise HTTPException(
            status_code=503,
            detail="Security audit is temporarily unavailable; document release denied",
        ) from exc


def _download_release_audit(
    *,
    current_user: User,
    doc: MedicalDocument,
    allowed: bool,
    denial_reason: Optional[str] = None,
    purpose: Optional[str] = None,
    consent_id: Optional[int] = None,
) -> AuditLog:
    return AuditLog(
        actor_id=current_user.id,
        actor_role=current_user.role,
        organization_id=doc.hospital_id,
        patient_id=doc.patient_id,
        operation="download_release",
        resource_type="document",
        resource_id=str(doc.id),
        purpose=purpose,
        consent_id=consent_id,
        decision="ALLOW" if allowed else "DENY",
        denial_reason=denial_reason,
        metadata_json=json.dumps({"scan_status": doc.scan_status}),
    )


@router.post("/documents", response_model=DocumentUploadResponse)
@limiter.limit("10/minute")
def upload_document(
    request: Request,
    visit_id: int = Form(...),
    document_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_practitioner_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    # 1. Validate visit
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # 2. Central Authorization — must be active member of visit's hospital
    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_doctor,
            operation=Operation.CREATE,
            resource_type=ResourceType.DOCUMENT,
            db=db,
            hospital_id=visit.hospital_id,
        )
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)

    # 3. Validate file type and size
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Invalid file type: {file.content_type}"
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if document_type not in [item.value for item in DocumentType]:
        raise HTTPException(status_code=400, detail="Invalid document type")

    # 4. Save file to private storage. If the database transaction later fails,
    # R7 performs a compensating delete so protected orphan objects are not left
    # behind indefinitely.
    storage_path = storage_service.upload_document(file, visit.patient_id)

    try:
        doc = MedicalDocument(
            patient_id=visit.patient_id,
            hospital_id=visit.hospital_id,
            uploaded_by_doctor_id=current_doctor.id,
            visit_id=visit.id,
            document_type=document_type,
            title=title,
            description=description,
            original_filename=file.filename,
            stored_filename=storage_path,
            mime_type=file.content_type,
            file_size=file_size,
            scan_status=SCAN_PENDING,
        )
        db.add(doc)
        db.flush()  # Get doc.id without committing

        audit = AuditLog(
            actor_id=current_doctor.id,
            actor_role="doctor",
            organization_id=visit.hospital_id,
            patient_id=visit.patient_id,
            operation="CREATE",
            resource_type="document",
            resource_id=str(doc.id),
            decision="ALLOW",
        )
        db.add(audit)

        notif = Notification(
            user_id=visit.patient_id,
            type="document_uploaded",
            message=f"New document uploaded: {doc.title}",
            related_document_id=doc.id,
        )
        db.add(notif)

        db.commit()
        db.refresh(doc)
        db.refresh(notif)
    except Exception as exc:
        db.rollback()
        try:
            storage_service.delete_document(storage_path)
        except Exception:
            # The original database failure still determines the HTTP result, but
            # cleanup failure is logged for operations/incident response.
            logger.exception(
                "Compensating deletion failed for storage_path=%s", storage_path
            )
        logger.exception("Document metadata transaction failed")
        raise HTTPException(
            status_code=500,
            detail="Document upload could not be finalized",
        ) from exc

    background_tasks.add_task(
        manager.send_personal_message,
        {
            "type": "document_uploaded",
            "data": {"document_id": doc.id, "title": doc.title},
        },
        visit.patient_id,
    )
    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "notification_created", "data": {"notification_id": notif.id}},
        visit.patient_id,
    )
    # R7: real ClamAV-backed scan. Scanner/storage failures become scan_error;
    # they never auto-promote an upload to clean.
    background_tasks.add_task(scan_document, doc.id)

    return {
        "id": doc.id,
        "message": "Document uploaded successfully and is pending malware scan",
    }


@router.get("/documents/patient", response_model=List[MedicalDocumentSchema])
def list_patient_documents(
    hospital_id: Optional[int] = None,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient_identity),
):
    query = db.query(MedicalDocument).filter(
        MedicalDocument.patient_id == current_patient.id
    )
    if hospital_id:
        query = query.filter(MedicalDocument.hospital_id == hospital_id)
    if document_type:
        query = query.filter(MedicalDocument.document_type == document_type)
    return query.all()


@router.get("/documents/metadata/{patient_id}", response_model=List[MedicalDocumentSchema])
def list_patient_document_metadata(
    patient_id: int,
    hospital_id: int = Query(..., gt=0),
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_practitioner_identity),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_doctor,
            operation=Operation.REQUEST_ACCESS,
            resource_type=ResourceType.ACCESS_REQUEST,
            db=db,
            hospital_id=hospital_id,
        )
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)

    has_visit = (
        db.query(Visit)
        .filter(
            Visit.patient_id == patient_id,
            Visit.doctor_id == current_doctor.id,
            Visit.hospital_id == hospital_id,
        )
        .first()
    )
    if not has_visit:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to discover documents for this patient in this organization",
        )

    # Allowed to list metadata (without content) so doctors can request access.
    query = db.query(MedicalDocument).filter(
        MedicalDocument.patient_id == patient_id,
        MedicalDocument.hospital_id == hospital_id,
    )
    return query.all()


@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    purpose: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    # Load resource before authorization (404 masks existence for unauthorized callers).
    doc = (
        db.query(MedicalDocument)
        .filter(MedicalDocument.id == document_id)
        .first()
    )

    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")

    trusted_grant = None
    if current_user.role == "doctor" and doc is not None:
        if purpose is None or not purpose.strip():
            raise HTTPException(
                status_code=403,
                detail="PURPOSE_REQUIRED: practitioner document download requires an explicit purpose",
            )
        trusted_grant = resolve_active_document_grant(
            db,
            doctor_id=current_user.id,
            document=doc,
        )

    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_user,
            operation=Operation.DOWNLOAD,
            resource_type=ResourceType.DOCUMENT,
            db=db,
            resource=doc,
            hospital_id=doc.hospital_id if doc else None,
            patient_id=doc.patient_id if doc else None,
            purpose=purpose,
            consent_id=(trusted_grant.consent_id if trusted_grant else None),
            relationship_context=trusted_grant,
        )
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=404 if decision.detail == "Document not found" else 403,
            detail=decision.detail,
        )

    # Malware enforcement is independent of authorization. Only an explicit
    # scanner-confirmed clean state may release bytes; every other state fails closed.
    if doc.scan_status != SCAN_CLEAN:
        reason = "malware_quarantine"
        _commit_security_audit(
            db,
            _download_release_audit(
                current_user=current_user,
                doc=doc,
                allowed=False,
                denial_reason=reason,
                purpose=purpose,
                consent_id=(trusted_grant.consent_id if trusted_grant else None),
            ),
        )
        if doc.scan_status == SCAN_MALICIOUS:
            raise HTTPException(
                status_code=403, detail="Document blocked: malware detected"
            )
        if doc.scan_status == SCAN_PENDING:
            raise HTTPException(
                status_code=403,
                detail="Document is currently in quarantine pending malware scan",
            )
        if doc.scan_status == SCAN_ERROR:
            raise HTTPException(
                status_code=403,
                detail="Document remains quarantined because malware scanning could not be completed",
            )
        raise HTTPException(
            status_code=403,
            detail="Document remains quarantined because its scan state is not releasable",
        )

    try:
        file_bytes = storage_service.download_document(doc.stored_filename)
    except HTTPException:
        _commit_security_audit(
            db,
            _download_release_audit(
                current_user=current_user,
                doc=doc,
                allowed=False,
                denial_reason="storage_unavailable",
                purpose=purpose,
                consent_id=(trusted_grant.consent_id if trusted_grant else None),
            ),
        )
        raise
    except Exception as exc:
        _commit_security_audit(
            db,
            _download_release_audit(
                current_user=current_user,
                doc=doc,
                allowed=False,
                denial_reason="storage_unavailable",
                purpose=purpose,
                consent_id=(trusted_grant.consent_id if trusted_grant else None),
            ),
        )
        raise HTTPException(
            status_code=503,
            detail="Document storage is temporarily unavailable",
        ) from exc

    # Commit both the CAE authorization audit already flushed by AuthorizationService
    # and the final enforcement/release result before returning protected bytes.
    _commit_security_audit(
        db,
        _download_release_audit(
            current_user=current_user,
            doc=doc,
            allowed=True,
            purpose=purpose,
            consent_id=(trusted_grant.consent_id if trusted_grant else None),
        ),
    )

    from fastapi.responses import StreamingResponse
    import io

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=doc.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{doc.original_filename}"'
        },
    )
