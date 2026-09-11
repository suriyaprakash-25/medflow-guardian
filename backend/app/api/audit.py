from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.notification import AuditLogSchema
from app.api.dependencies import get_current_active_user, get_authorization_service
from app.services.authorization import (
    AuthorizationService, AuthorizationContext, Operation, ResourceType
)

router = APIRouter()

@router.get("/audit/patient", response_model=List[AuditLogSchema])
def get_patient_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service)
):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.AUDIT_LOG,
        db=db
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)

    if current_user.role != "patient":
        raise HTTPException(status_code=403, detail="Only patients can access their audit logs this way")
        
    return db.query(AuditLog).filter(
        AuditLog.patient_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).all()

@router.get("/audit/doctor", response_model=List[AuditLogSchema])
def get_doctor_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service)
):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.AUDIT_LOG,
        db=db
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)

    if current_user.role != "doctor":
        raise HTTPException(status_code=403, detail="Only doctors can access their audit logs this way")
        
    return db.query(AuditLog).filter(
        AuditLog.actor_id == current_user.id
    ).order_by(AuditLog.timestamp.desc()).all()
