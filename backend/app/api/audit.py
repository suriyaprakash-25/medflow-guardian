from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.hospital import HospitalStaff
from app.models.audit import AuditLog
from app.schemas.notification import AuditLogSchema
from app.api.dependencies import get_current_user

router = APIRouter()

@router.get("/audit/patient", response_model=List[AuditLogSchema])
def get_patient_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access their audit logs this way")
        
    return db.query(AuditLog).filter(
        AuditLog.patient_id == current_user.id
    ).order_by(AuditLog.created_at.desc()).all()

@router.get("/audit/doctor", response_model=List[AuditLogSchema])
def get_doctor_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access their audit logs this way")
        
    # Doctor can view events where they are the actor
    # Or events related to patients they have active interactions with (for simplicity, we restrict to actor_id for now as per requirements: "Doctors can view only appropriate events related to their actions.")
    
    return db.query(AuditLog).filter(
        AuditLog.actor_id == current_user.id
    ).order_by(AuditLog.created_at.desc()).all()
