import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.limiter import limiter

from app.core.database import get_db
from app.models.user import User
from app.models.hospital import Visit, HospitalStaff
from app.models.document import MedicalDocument, DocumentType
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.api.websockets import manager
from app.schemas.document import MedicalDocumentSchema, DocumentUploadResponse
from app.api.dependencies import get_current_user, get_patient_identity, get_practitioner_identity, get_authorization_service
from app.services.storage import storage_service
from app.services.authorization import (
    AuthorizationService, AuthorizationContext, Operation, ResourceType
)
import asyncio

async def mock_malware_scan(document_id: int):
    # Mocking a malware scan that takes 5 seconds then sets the document to clean.
    # In a real architecture, this would send to an isolated scanning worker via SQS/Celery.
    await asyncio.sleep(5)
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
        if doc:
            doc.scan_status = "clean"
            db.commit()
    finally:
        db.close()

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

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
    auth_svc: AuthorizationService = Depends(get_authorization_service)
):
    # 1. Validate visit
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # 2. Central Authorization — must be active member of visit's hospital
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_doctor,
        operation=Operation.CREATE,
        resource_type=ResourceType.DOCUMENT,
        db=db,
        hospital_id=visit.hospital_id
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)

    # 3. Validate file type and size
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type: {file.content_type}")
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    if document_type not in [item.value for item in DocumentType]:
        raise HTTPException(status_code=400, detail="Invalid document type")

    # 4. Save file securely via StorageService
    storage_path = storage_service.upload_document(file, visit.patient_id)

    # 5. Database record (bundled transaction)
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
            file_size=file_size
        )
        db.add(doc)
        db.flush() # Get doc.id without committing

        # Phase 4: Audit & Notifications
        audit = AuditLog(
            actor_id=current_doctor.id,
            actor_role="doctor",
            organization_id=visit.hospital_id,
            patient_id=visit.patient_id,
            operation="CREATE",
            resource_type="document",
            resource_id=str(doc.id),
            decision="ALLOW"
        )
        db.add(audit)
        
        notif = Notification(
            user_id=visit.patient_id,
            type="document_uploaded",
            message=f"New document uploaded: {doc.title}",
            related_document_id=doc.id
        )
        db.add(notif)
        
        db.commit()
        db.refresh(doc)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database transaction failed: {str(e)}")

    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "document_uploaded", "data": {"document_id": doc.id, "title": doc.title}},
        visit.patient_id
    )
    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "notification_created", "data": {"message": notif.message}},
        visit.patient_id
    )
    background_tasks.add_task(mock_malware_scan, doc.id)

    return {"id": doc.id, "message": "Document uploaded successfully and is pending malware scan"}

@router.get("/documents/patient", response_model=List[MedicalDocumentSchema])
def list_patient_documents(
    hospital_id: Optional[int] = None,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient_identity)
):
    query = db.query(MedicalDocument).filter(MedicalDocument.patient_id == current_patient.id)
    if hospital_id:
        query = query.filter(MedicalDocument.hospital_id == hospital_id)
    if document_type:
        query = query.filter(MedicalDocument.document_type == document_type)
    return query.all()

@router.get("/documents/metadata/{patient_id}", response_model=List[MedicalDocumentSchema])
def list_patient_document_metadata(
    patient_id: int,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_practitioner_identity)
):
    # Ensure the doctor has had at least one visit with this patient
    from app.models.hospital import Visit
    has_visit = db.query(Visit).filter(Visit.patient_id == patient_id, Visit.doctor_id == current_doctor.id).first()
    if not has_visit:
        raise HTTPException(status_code=403, detail="Not authorized to query this patient's records")

    # Allowed to list metadata (without content) so doctors can request access
    query = db.query(MedicalDocument).filter(MedicalDocument.patient_id == patient_id)
    return query.all()

@router.get("/documents/{document_id}/download")
def download_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    purpose: Optional[str] = None,
    enforcement_state_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service)
):
    # Load resource before authorization (404 masks existence for unauthorized callers)
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()

    # Central Authorization — hides existence for unauthenticated/unauthorized actors
    if not current_user or not current_user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required")

    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user,
        operation=Operation.DOWNLOAD,
        resource_type=ResourceType.DOCUMENT,
        db=db,
        resource=doc,  # None if not found; engine handles 404 denial
        hospital_id=doc.hospital_id if doc else None,
        patient_id=doc.patient_id if doc else None,
        purpose=purpose,
        enforcement_state_id=enforcement_state_id
    ))
    if not decision.allowed:
        # Use 404 to avoid leaking document existence to unauthorized actors
        raise HTTPException(
            status_code=404 if decision.detail == "Document not found" else 403,
            detail=decision.detail
        )

    if doc.scan_status == "pending":
        raise HTTPException(status_code=403, detail="Document is currently in quarantine pending malware scan")
    if doc.scan_status == "malicious":
        raise HTTPException(status_code=403, detail="Document blocked: malware detected")

    # Audit log (moved before download to ensure we capture the intent)
    audit = AuditLog(
        actor_id=current_user.id,
        actor_role=current_user.role,
        organization_id=doc.hospital_id,
        patient_id=doc.patient_id,
        operation="DOWNLOAD",
        resource_type="document",
        resource_id=str(doc.id),
        decision="ALLOW"
    )
    db.add(audit)
    db.commit()

    try:
        file_bytes = storage_service.download_document(doc.stored_filename)
        from fastapi.responses import StreamingResponse
        import io
        return StreamingResponse(
            io.BytesIO(file_bytes), 
            media_type=doc.mime_type, 
            headers={"Content-Disposition": f'attachment; filename="{doc.original_filename}"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
