from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from app.core.database import get_db
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff
from app.models.audit import AuditLog
from app.models.access import DocumentAccessRequest, DocumentAccessGrant
from app.models.consent import ConsentState
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType

router = APIRouter()

@router.get("/dashboard")
def get_dashboard_metrics(
    hospital_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Determine org scope
    if current_user.role != "platform_admin":
        if current_user.role == "patient":
            raise HTTPException(status_code=403, detail="Patients are not authorized to view the admin dashboard")
        if not hospital_id:
            raise HTTPException(status_code=400, detail="hospital_id is required for organization admins")
            
        auth_svc = AuthorizationService(db)
        ctx = AuthorizationContext(
            actor=current_user,
            operation=Operation.VIEW_DASHBOARD,
            resource_type=ResourceType.HOSPITAL,
            db=db,
            hospital_id=hospital_id
        )
        # We can reuse the staff rule or write a dashboard check. 
        # For simplicity, if they can manage staff, they can view the dashboard.
        ctx.operation = Operation.MANAGE_STAFF
        ctx.resource_type = ResourceType.STAFF
        decision = auth_svc.authorize(ctx)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.reason)

    # Gather metrics
    org_filter = [HospitalStaff.hospital_id == hospital_id] if hospital_id else []
    
    total_staff = db.query(HospitalStaff).filter(*org_filter, HospitalStaff.is_active == True).count()
    
    # Active consent states
    # Active consent states - Note: Consents are patient-centric, not hospital-centric. We'll show a global metric for now.
    active_consents = db.query(ConsentState).filter(ConsentState.status == "active").count()

    total_patients = db.query(User).filter(User.role == "patient").count() # Basic metric
    
    recent_audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5).all()
    
    return {
        "metrics": {
            "total_staff": total_staff,
            "active_consents": active_consents,
            "total_patients": total_patients
        },
        "recent_activity": recent_audits
    }

@router.get("/staff")
def get_staff(
    hospital_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.STAFF,
        db=db,
        hospital_id=hospital_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    staff_members = db.query(HospitalStaff).filter(HospitalStaff.hospital_id == hospital_id).all()
    result = []
    for s in staff_members:
        user = db.query(User).filter(User.id == s.user_id).first()
        result.append({
            "membership_id": s.id,
            "user_id": s.user_id,
            "email": user.email if user else "Unknown",
            "full_name": user.full_name if user else "Unknown",
            "role": s.role,
            "is_active": s.is_active,
            "joined_at": s.joined_at
        })
    return result

@router.get("/audit")
def get_audit_logs(
    hospital_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # This requires platform admin OR org admin checking their own hospital
    if current_user.role != "platform_admin":
        if not hospital_id:
            raise HTTPException(status_code=400, detail="hospital_id required for org admins")
        
        # Check org admin
        auth_svc = AuthorizationService(db)
        ctx = AuthorizationContext(
            actor=current_user,
            operation=Operation.MANAGE_STAFF, # Using staff management as a proxy for org admin
            resource_type=ResourceType.STAFF,
            db=db,
            hospital_id=hospital_id
        )
        decision = auth_svc.authorize(ctx)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail="Not authorized to view audit logs for this organization")

    query = db.query(AuditLog)
    if hospital_id:
        query = query.filter(AuditLog.organization_id == hospital_id)
        
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "items": logs,
        "total": total,
        "limit": limit,
        "offset": offset
    }
