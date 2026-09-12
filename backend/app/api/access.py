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
from app.models.consent import Consent, ConsentPolicyVersion, ConsentState
from app.models.audit import AuditLog
from app.models.notification import Notification
from app.api.websockets import manager
from app.schemas.access import (
    AccessRequestCreate, AccessRequestResponse, 
    AccessRequestApprove, AccessRequestReject, AccessGrantResponse
)
from app.api.dependencies import get_current_user, get_patient_identity, get_practitioner_identity

router = APIRouter()

@router.post("/access-requests", response_model=AccessRequestResponse)
def create_access_request(
    request_data: AccessRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_practitioner_identity)
):
    # Verify doctor is affiliated with the requested hospital
    membership = db.query(HospitalStaff).filter(
        HospitalStaff.user_id == current_doctor.id,
        HospitalStaff.hospital_id == request_data.hospital_id,
        HospitalStaff.is_active == True
    ).first()
    if not membership:
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
        organization_id=request_data.hospital_id,
        patient_id=request_data.patient_id,
        operation="request_access",
        resource_type="access_request",
        resource_id=str(access_req.id),
        decision="ALLOW"
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
    current_doctor: User = Depends(get_practitioner_identity)
):
    requests = db.query(DocumentAccessRequest).filter(
        DocumentAccessRequest.requesting_doctor_id == current_doctor.id
    ).all()
    return requests

@router.get("/access-requests/patient", response_model=List[AccessRequestResponse])
def get_patient_requests(
    status: str = None,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient_identity)
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
    current_patient: User = Depends(get_patient_identity)
):
    # Verify durations (1, 4, 24, 96 hours)
    if approval_data.duration_hours not in [1, 4, 24, 96]:
        raise HTTPException(status_code=400, detail="Invalid expiry duration")

    # Phase 8: Concurrency Control - Lock the request to prevent duplicate approvals
    req = db.query(DocumentAccessRequest).with_for_update().filter(
        DocumentAccessRequest.id == request_id
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.patient_id != current_patient.id:
        raise HTTPException(status_code=403, detail="Not authorized to approve this request")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    # Approve
    req.status = "approved"
    req.responded_at = datetime.utcnow()

    # Validate selected docs (if any were provided)
    approved_docs = []
    if approval_data.document_ids:
        approved_docs = db.query(MedicalDocument).filter(
            MedicalDocument.id.in_(approval_data.document_ids),
            MedicalDocument.patient_id == current_patient.id
        ).all()

    # Phase 5: Create Governance Entities (Consent, Policy, State)
    consent = Consent(
        patient_id=current_patient.id,
        doctor_id=req.requesting_doctor_id,
        hospital_id=req.requesting_hospital_id,
        status="active"
    )
    db.add(consent)
    db.flush()

    policy = ConsentPolicyVersion(
        consent_id=consent.id,
        version_number=1,
        policy_payload={"allowed_purposes": ["TREATMENT"], "allowed_operations": ["READ", "DOWNLOAD"]},
        status="active"
    )
    db.add(policy)
    db.flush()

    state = ConsentState(
        consent_id=consent.id,
        policy_version_id=policy.id,
        status="active"
    )
    db.add(state)
    db.flush()

    # Create Grant
    expires_at = datetime.utcnow() + timedelta(hours=approval_data.duration_hours)
    
    grant = DocumentAccessGrant(
        access_request_id=req.id,
        patient_id=current_patient.id,
        doctor_id=req.requesting_doctor_id,
        hospital_id=req.requesting_hospital_id,
        consent_id=consent.id,
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
        organization_id=req.requesting_hospital_id,
        patient_id=current_patient.id,
        operation="grant_access",
        resource_type="access_request",
        resource_id=str(req.id),
        consent_id=consent.id,
        consent_state_id=state.id,
        decision="ALLOW"
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
    current_patient: User = Depends(get_patient_identity)
):
    # Phase 8: Concurrency Control - Lock the request
    req = db.query(DocumentAccessRequest).with_for_update().filter(
        DocumentAccessRequest.id == request_id
    ).first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if req.patient_id != current_patient.id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this request")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {req.status}")

    req.status = "rejected"
    req.responded_at = datetime.utcnow()
    req.rejection_reason = reject_data.rejection_reason
    
    # Phase 4 Audit and Notification
    audit = AuditLog(
        actor_id=current_patient.id,
        actor_role="patient",
        organization_id=req.requesting_hospital_id,
        patient_id=current_patient.id,
        operation="reject_access",
        resource_type="access_request",
        resource_id=str(req.id),
        decision="ALLOW"
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
    current_patient: User = Depends(get_patient_identity)
):
    # Phase 8: Concurrency Control - Lock the grant to prevent concurrent revocations
    grant = db.query(DocumentAccessGrant).with_for_update().filter(
        DocumentAccessGrant.id == grant_id,
        DocumentAccessGrant.patient_id == current_patient.id
    ).first()

    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if grant.status != "active":
        raise HTTPException(status_code=400, detail="Grant is not active")

    grant.status = "revoked"
    grant.revoked_at = datetime.utcnow()
    
    # Phase 5: Update Authoritative Consent State
    if grant.consent_id:
        # Phase 8: Lock the consent row to serialize state transitions
        consent = db.query(Consent).with_for_update().filter(Consent.id == grant.consent_id).first()
        if consent:
            consent.status = "revoked"
            # Get latest policy
            policy = db.query(ConsentPolicyVersion).filter(
                ConsentPolicyVersion.consent_id == consent.id,
                ConsentPolicyVersion.status == "active"
            ).first()
            if policy:
                state = ConsentState(
                    consent_id=consent.id,
                    policy_version_id=policy.id,
                    status="revoked"
                )
                db.add(state)
    
    # Also update the request status for clarity
    if grant.request:
        grant.request.status = "revoked"

    # Phase 4 Audit and Notification
    audit = AuditLog(
        actor_id=current_patient.id,
        actor_role="patient",
        organization_id=grant.hospital_id,
        patient_id=current_patient.id,
        operation="revoke_access",
        resource_type="access_grant",
        resource_id=str(grant.id),
        consent_id=grant.consent_id,
        decision="ALLOW"
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
    current_patient: User = Depends(get_patient_identity)
):
    return db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.patient_id == current_patient.id
    ).all()

@router.get("/access-grants/doctor", response_model=List[AccessGrantResponse])
def get_doctor_grants(
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_practitioner_identity)
):
    grants = db.query(DocumentAccessGrant).filter(
        DocumentAccessGrant.doctor_id == current_doctor.id
    ).all()

    # Automatically mark expired grants as such in memory for the response
    # (A background job or access-check handles true expiration, but for UI clarity we check it here)
    from datetime import timezone
    for g in grants:
        if g.status == "active" and g.expires_at < datetime.now(timezone.utc):
            g.status = "expired"
    
    return grants
