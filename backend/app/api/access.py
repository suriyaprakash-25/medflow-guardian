from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.hospital import HospitalStaff
from app.models.document import MedicalDocument
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.api.websockets import manager
from app.schemas.access import (
    AccessRequestCreate, AccessRequestResponse, 
    AccessRequestApprove, AccessRequestReject, AccessGrantResponse
)
from app.api.dependencies import get_current_user, get_current_patient, get_current_doctor

router = APIRouter()

@router.post("/access-requests", response_model=AccessRequestResponse)
def create_access_request(
    request_data: AccessRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor)
):
    # Verify doctor is affiliated with the requested hospital
    affiliations = db.query(HospitalStaff).filter(HospitalStaff.user_id == current_doctor.id).all()
    if request_data.hospital_id not in [aff.hospital_id for aff in affiliations]:
        raise HTTPException(status_code=403, detail="Not authorized to request on behalf of this hospital")

    # Verify documents belong to patient
    requested_docs = db.query(MedicalDocument).filter(
        MedicalDocument.id.in_(request_data.document_ids),
        MedicalDocument.patient_id == request_data.patient_id
    ).all()

    if len(requested_docs) != len(request_data.document_ids):
        raise HTTPException(status_code=400, detail="One or more documents invalid or do not belong to patient")

    access_req = DocumentAccessRequest(
        patient_id=request_data.patient_id,
        requesting_doctor_id=current_doctor.id,
        requesting_hospital_id=request_data.hospital_id,
        reason=request_data.reason,
        status="pending"
    )
    access_req.requested_documents.extend(requested_docs)
    
    db.add(access_req)
    db.commit()
    db.refresh(access_req)

    # Phase 4 Audit and Notification
    audit = AuditLog(
        actor_id=current_doctor.id,
        actor_role="doctor",
        hospital_id=request_data.hospital_id,
        patient_id=request_data.patient_id,
        action="access requested",
        access_request_id=access_req.id
    )
    db.add(audit)

    notif = Notification(
        user_id=request_data.patient_id,
        type="access_request_created",
        message=f"Doctor {current_doctor.id} requested access to your documents.",
        related_request_id=access_req.id
    )
    db.add(notif)
    db.commit()

    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "access_request_created", "data": {"request_id": access_req.id}},
        request_data.patient_id
    )
    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "notification_created", "data": {"message": notif.message}},
        request_data.patient_id
    )

    return access_req

@router.get("/access-requests/doctor", response_model=List[AccessRequestResponse])
def get_doctor_requests(
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor)
):
    requests = db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.requesting_doctor_id == current_doctor.id
    ).all()
    return requests

@router.get("/access-requests/patient", response_model=List[AccessRequestResponse])
def get_patient_requests(
    status: str = None,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    query = db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.patient_id == current_patient.id
    )
    if status:
        query = query.filter(DocumentAccessRequest.status == status)
    return query.all()

@router.post("/access-requests/{request_id}/approve", response_model=AccessGrantResponse)
def approve_request(
    request_id: int,
    approval_data: AccessRequestApprove,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    # Verify durations (1, 4, 24, 96 hours)
    if approval_data.duration_hours not in [1, 4, 24, 96]:
        raise HTTPException(status_code=400, detail="Invalid expiry duration")

    req = db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.id == request_id,
        DocumentAccessRequest.patient_id == current_patient.id
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    # Approve
    req.status = "approved"
    req.responded_at = datetime.utcnow()

    # Validate selected docs
    approved_docs = db.query(MedicalDocument).filter(
        MedicalDocument.id.in_(approval_data.document_ids),
        MedicalDocument.patient_id == current_patient.id
    ).all()

    if not approved_docs:
        raise HTTPException(status_code=400, detail="No valid documents selected")

    # Create Grant
    expires_at = datetime.utcnow() + timedelta(hours=approval_data.duration_hours)
    
    grant = DocumentAccessGrant(
        access_request_id=req.id,
        patient_id=current_patient.id,
        doctor_id=req.requesting_doctor_id,
        hospital_id=req.requesting_hospital_id,
        status="active",
        expires_at=expires_at
    )
    grant.granted_documents.extend(approved_docs)

    db.add(grant)
    db.commit()
    db.refresh(grant)

    # Phase 4 Audit and Notification
    audit = AuditLog(
        actor_id=current_patient.id,
        actor_role="patient",
        hospital_id=req.requesting_hospital_id,
        patient_id=current_patient.id,
        action="access approved",
        access_request_id=req.id,
        access_grant_id=grant.id
    )
    db.add(audit)

    notif = Notification(
        user_id=req.requesting_doctor_id,
        type="access_request_approved",
        message=f"Patient {current_patient.id} approved your document access request.",
        related_request_id=req.id
    )
    db.add(notif)
    db.commit()

    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "access_request_approved", "data": {"request_id": req.id, "grant_id": grant.id}},
        req.requesting_doctor_id
    )
    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "notification_created", "data": {"message": notif.message}},
        req.requesting_doctor_id
    )

    return grant

@router.post("/access-requests/{request_id}/reject")
def reject_request(
    request_id: int,
    reject_data: AccessRequestReject,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    req = db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.id == request_id,
        DocumentAccessRequest.patient_id == current_patient.id
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "rejected"
    req.responded_at = datetime.utcnow()
    req.rejection_reason = reject_data.rejection_reason
    
    # Phase 4 Audit and Notification
    audit = AuditLog(
        actor_id=current_patient.id,
        actor_role="patient",
        hospital_id=req.requesting_hospital_id,
        patient_id=current_patient.id,
        action="access rejected",
        access_request_id=req.id
    )
    db.add(audit)

    notif = Notification(
        user_id=req.requesting_doctor_id,
        type="access_request_rejected",
        message=f"Patient {current_patient.id} rejected your document access request.",
        related_request_id=req.id
    )
    db.add(notif)
    db.commit()

    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "access_request_rejected", "data": {"request_id": req.id}},
        req.requesting_doctor_id
    )
    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "notification_created", "data": {"message": notif.message}},
        req.requesting_doctor_id
    )

    return {"message": "Request rejected"}

@router.post("/access-grants/{grant_id}/revoke")
def revoke_grant(
    grant_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    grant = db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.id == grant_id,
        DocumentAccessGrant.patient_id == current_patient.id
    ).first()

    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if grant.status != "active":
        raise HTTPException(status_code=400, detail="Grant is not active")

    grant.status = "revoked"
    grant.revoked_at = datetime.utcnow()
    
    # Also update the request status for clarity
    if grant.request:
        grant.request.status = "revoked"

    # Phase 4 Audit and Notification
    audit = AuditLog(
        actor_id=current_patient.id,
        actor_role="patient",
        hospital_id=grant.hospital_id,
        patient_id=current_patient.id,
        action="access revoked",
        access_grant_id=grant.id
    )
    db.add(audit)

    notif = Notification(
        user_id=grant.doctor_id,
        type="access_revoked",
        message=f"Patient {current_patient.id} revoked access to their documents."
    )
    db.add(notif)
    db.commit()

    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "access_revoked", "data": {"grant_id": grant.id}},
        grant.doctor_id
    )
    background_tasks.add_task(
        manager.send_personal_message,
        {"type": "notification_created", "data": {"message": notif.message}},
        grant.doctor_id
    )

    return {"message": "Access revoked successfully"}

@router.get("/access-grants/patient", response_model=List[AccessGrantResponse])
def get_patient_grants(
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    return db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.patient_id == current_patient.id
    ).all()

@router.get("/access-grants/doctor", response_model=List[AccessGrantResponse])
def get_doctor_grants(
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor)
):
    grants = db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.doctor_id == current_doctor.id
    ).all()

    # Automatically mark expired grants as such in memory for the response
    # (A background job or access-check handles true expiration, but for UI clarity we check it here)
    for g in grants:
        if g.status == "active" and g.expires_at < datetime.utcnow():
            g.status = "expired"
    
    return grants
