import os
import uuid
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.hospital import Visit, HospitalStaff
from app.models.document import MedicalDocument, DocumentType
from app.models.notification import Notification
from app.models.audit import AuditLog
from app.api.websockets import manager
from app.schemas.document import MedicalDocumentSchema, DocumentUploadResponse
from app.api.dependencies import get_current_user, get_current_patient, get_current_doctor

router = APIRouter()

STORAGE_DIR = os.environ.get("MEDFLOW_STORAGE_DIR", "storage/documents")
os.makedirs(STORAGE_DIR, exist_ok=True)

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain"
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/documents", response_model=DocumentUploadResponse)
def upload_document(
    visit_id: int = Form(...),
    document_type: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor)
):
    # 1. Validate visit
    visit = db.query(Visit).filter(Visit.id == visit_id).first()
    if not visit:
        raise HTTPException(status_code=404, detail="Visit not found")

    # 2. Validate doctor authorization for this visit's hospital
    affiliations = db.query(HospitalStaff).filter(HospitalStaff.user_id == current_doctor.id).all()
    hospital_ids = [aff.hospital_id for aff in affiliations]
    if visit.hospital_id not in hospital_ids:
        raise HTTPException(status_code=403, detail="Not authorized to upload documents for this hospital's visits")

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

    # 4. Save file securely
    import re
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".jpg", ".jpeg", ".png", ".txt"]:
        raise HTTPException(status_code=400, detail="Invalid file extension")
    
    safe_filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = os.path.join(STORAGE_DIR, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. Database record
    doc = MedicalDocument(
        patient_id=visit.patient_id,
        hospital_id=visit.hospital_id,
        uploaded_by_doctor_id=current_doctor.id,
        visit_id=visit.id,
        document_type=document_type,
        title=title,
        description=description,
        original_filename=file.filename,
        stored_filename=safe_filename,
        mime_type=file.content_type,
        file_size=file_size
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Phase 4: Audit & Notifications
    audit = AuditLog(
        actor_id=current_doctor.id,
        actor_role="doctor",
        hospital_id=visit.hospital_id,
        patient_id=visit.patient_id,
        action="document uploaded",
        document_id=doc.id
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

    return {"id": doc.id, "message": "Document uploaded successfully"}

@router.get("/documents/patient", response_model=List[MedicalDocumentSchema])
def list_patient_documents(
    hospital_id: Optional[int] = None,
    document_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
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
    current_doctor: User = Depends(get_current_doctor)
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    doc = db.query(MedicalDocument).filter(MedicalDocument.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Authorization Check
    if current_user.role == "patient":
        if doc.patient_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this document")
    elif current_user.role == "doctor":
        # 1. Check hospital affiliations
        affiliations = db.query(HospitalStaff).filter(HospitalStaff.user_id == current_user.id).all()
        hospital_ids = [aff.hospital_id for aff in affiliations]
        
        has_affiliation_access = doc.hospital_id in hospital_ids or doc.uploaded_by_doctor_id == current_user.id
        
        # 2. Check active access grants
        if not has_affiliation_access:
            from app.models.access import DocumentAccessGrant
            from datetime import datetime
            
            # Find an active grant for this doctor and this document
            active_grant = db.query(DocumentAccessGrant).filter(
                DocumentAccessGrant.doctor_id == current_user.id,
                DocumentAccessGrant.status == "active",
                DocumentAccessGrant.expires_at > datetime.utcnow()
            ).filter(
                DocumentAccessGrant.granted_documents.any(id=doc.id)
            ).first()
            
            if not active_grant:
                raise HTTPException(status_code=403, detail="Not authorized to access this patient's document")
    else:
        raise HTTPException(status_code=403, detail="Invalid role")

    file_path = os.path.join(STORAGE_DIR, doc.stored_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing on disk")

    # Audit log
    audit = AuditLog(
        actor_id=current_user.id,
        actor_role=current_user.role,
        hospital_id=doc.hospital_id,
        patient_id=doc.patient_id,
        action="document downloaded",
        document_id=doc.id
    )
    db.add(audit)
    db.commit()

    return FileResponse(file_path, media_type=doc.mime_type, filename=doc.original_filename)
