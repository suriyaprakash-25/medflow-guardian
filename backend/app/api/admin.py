from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.models.user import User
from app.models.hospital import Hospital, HospitalStaff
from app.models.audit import AuditLog
from app.models.consent import ConsentState
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType
from app.schemas.admin import HospitalCreate, HospitalUpdate, StaffCreate, StaffUpdate
from app.schemas.hospital import Hospital as HospitalSchema
from app.core.security import get_password_hash

router = APIRouter()


@router.get("/dashboard")
def get_dashboard_metrics(hospital_id: Optional[int] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "platform_admin":
        if current_user.role == "patient":
            raise HTTPException(status_code=403, detail="Patients are not authorized to view the admin dashboard")
        if not hospital_id:
            raise HTTPException(status_code=400, detail="hospital_id is required for organization admins")
        auth_svc = AuthorizationService(db)
        ctx = AuthorizationContext(actor=current_user, operation=Operation.MANAGE_STAFF, resource_type=ResourceType.STAFF, db=db, hospital_id=hospital_id)
        decision = auth_svc.authorize(ctx)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail=decision.reason)

    org_filter = [HospitalStaff.hospital_id == hospital_id] if hospital_id else []
    total_staff = db.query(HospitalStaff).filter(*org_filter, HospitalStaff.is_active == True).count()
    active_consents = db.query(ConsentState).filter(ConsentState.status == "active").count()
    total_patients = db.query(User).filter(User.role == "patient").count()
    recent_audits = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(5).all()
    return {"metrics": {"total_staff": total_staff, "active_consents": active_consents, "total_patients": total_patients}, "recent_activity": recent_audits}


@router.get("/staff")
def get_staff(hospital_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(actor=current_user, operation=Operation.LIST, resource_type=ResourceType.STAFF, db=db, hospital_id=hospital_id)
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    staff_members = db.query(HospitalStaff).filter(HospitalStaff.hospital_id == hospital_id).all()
    result = []
    for membership in staff_members:
        user = db.query(User).filter(User.id == membership.user_id).first()
        result.append({
            "membership_id": membership.id,
            "user_id": membership.user_id,
            "email": user.email if user else "Unknown",
            "full_name": user.full_name if user else "Unknown",
            "role": membership.role,
            "is_active": membership.is_active,
            "joined_at": membership.joined_at,
        })
    return result


@router.get("/audit")
def get_audit_logs(hospital_id: Optional[int] = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if limit < 1 or limit > 200 or offset < 0:
        raise HTTPException(status_code=400, detail="Invalid pagination")
    if current_user.role != "platform_admin":
        if not hospital_id:
            raise HTTPException(status_code=400, detail="hospital_id required for org admins")
        auth_svc = AuthorizationService(db)
        ctx = AuthorizationContext(actor=current_user, operation=Operation.MANAGE_STAFF, resource_type=ResourceType.STAFF, db=db, hospital_id=hospital_id)
        decision = auth_svc.authorize(ctx)
        if not decision.allowed:
            raise HTTPException(status_code=403, detail="Not authorized to view audit logs for this organization")

    query = db.query(AuditLog)
    if hospital_id:
        query = query.filter(AuditLog.organization_id == hospital_id)
    logs = query.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return {"items": logs, "total": query.count(), "limit": limit, "offset": offset}


@router.post("/organization", response_model=HospitalSchema)
def create_organization(data: HospitalCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    decision = AuthorizationService(db).authorize(AuthorizationContext(actor=current_user, operation=Operation.MANAGE_ORGANIZATIONS, resource_type=ResourceType.HOSPITAL, db=db))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    hospital = Hospital(name=data.name, address=data.address, contact_info=data.contact_info, is_active=data.is_active)
    db.add(hospital)
    db.commit()
    db.refresh(hospital)
    return hospital


@router.put("/organization/{hospital_id}", response_model=HospitalSchema)
def update_organization(hospital_id: int, data: HospitalUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    decision = AuthorizationService(db).authorize(AuthorizationContext(actor=current_user, operation=Operation.UPDATE, resource_type=ResourceType.HOSPITAL, db=db, hospital_id=hospital_id))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    if data.name is not None:
        hospital.name = data.name
    if data.address is not None:
        hospital.address = data.address
    if data.contact_info is not None:
        hospital.contact_info = data.contact_info
    if data.is_active is not None:
        hospital.is_active = data.is_active
    db.commit()
    db.refresh(hospital)
    return hospital


@router.post("/staff")
def provision_staff(hospital_id: int, data: StaffCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    decision = AuthorizationService(db).authorize(AuthorizationContext(actor=current_user, operation=Operation.MANAGE_STAFF, resource_type=ResourceType.STAFF, db=db, hospital_id=hospital_id))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        if not data.password:
            raise HTTPException(status_code=400, detail="password is required when provisioning a new account")
        user = User(
            email=data.email,
            hashed_password=get_password_hash(data.password),
            role="doctor",
            full_name=data.full_name or data.email.split("@")[0],
        )
        db.add(user)
        db.flush()

    existing = db.query(HospitalStaff).filter(HospitalStaff.user_id == user.id, HospitalStaff.hospital_id == hospital_id).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.role = data.role
            db.commit()
            db.refresh(existing)
            return {"message": "Reactivated staff", "membership_id": existing.id}
        raise HTTPException(status_code=400, detail="User is already active staff here")

    staff = HospitalStaff(user_id=user.id, hospital_id=hospital_id, role=data.role, is_active=True)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return {"message": "Staff provisioned successfully", "membership_id": staff.id}


@router.put("/staff/{membership_id}")
def update_staff(hospital_id: int, membership_id: int, data: StaffUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    decision = AuthorizationService(db).authorize(AuthorizationContext(actor=current_user, operation=Operation.MANAGE_STAFF, resource_type=ResourceType.STAFF, db=db, hospital_id=hospital_id))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    staff = db.query(HospitalStaff).filter(HospitalStaff.id == membership_id, HospitalStaff.hospital_id == hospital_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff membership not found in this hospital")
    if data.role is not None:
        staff.role = data.role
    if data.is_active is not None:
        staff.is_active = data.is_active
    db.commit()
    return {"message": "Staff updated successfully"}


@router.delete("/staff/{membership_id}")
def remove_staff(hospital_id: int, membership_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    decision = AuthorizationService(db).authorize(AuthorizationContext(actor=current_user, operation=Operation.MANAGE_STAFF, resource_type=ResourceType.STAFF, db=db, hospital_id=hospital_id))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
    staff = db.query(HospitalStaff).filter(HospitalStaff.id == membership_id, HospitalStaff.hospital_id == hospital_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff membership not found")
    staff.is_active = False
    db.commit()
    return {"message": "Staff deactivated successfully"}
