from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.hospital import Hospital, Visit, HospitalStaff
from app.models.user import User
from app.models.document import MedicalDocument
from app.schemas.hospital import Hospital as HospitalSchema, VisitWithDetails
from app.api.dependencies import get_authorization_service, get_current_user, get_patient_identity, get_practitioner_identity
from app.services.authorization import AuthorizationContext, AuthorizationService, Operation, ResourceType

router = APIRouter()

@router.get("/hospitals", response_model=List[HospitalSchema])
def list_hospitals(db: Session = Depends(get_db), current_user: User = Depends(get_current_user), auth_svc: AuthorizationService = Depends(get_authorization_service)):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user, operation=Operation.LIST, resource_type=ResourceType.HOSPITAL, db=db,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    return db.query(Hospital).filter(Hospital.is_active == True).all()

@router.get("/hospitals/{hospital_id}", response_model=HospitalSchema)
def get_hospital(hospital_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user), auth_svc: AuthorizationService = Depends(get_authorization_service)):
    hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
    if not hospital:
        raise HTTPException(status_code=404, detail="Hospital not found")
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_user, operation=Operation.READ, resource_type=ResourceType.HOSPITAL,
        db=db, resource=hospital, hospital_id=hospital_id,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    return hospital

@router.get("/visits/patient", response_model=List[VisitWithDetails])
def get_patient_visits(db: Session = Depends(get_db), current_patient: User = Depends(get_patient_identity), auth_svc: AuthorizationService = Depends(get_authorization_service)):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_patient, operation=Operation.LIST, resource_type=ResourceType.VISIT,
        db=db, patient_id=current_patient.id,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    visits = db.query(Visit).filter(Visit.patient_id == current_patient.id).all()
    return visits

@router.get("/visits/doctor", response_model=List[VisitWithDetails])
def get_doctor_visits(db: Session = Depends(get_db), current_doctor: User = Depends(get_practitioner_identity), auth_svc: AuthorizationService = Depends(get_authorization_service)):
    decision = auth_svc.authorize(AuthorizationContext(
        actor=current_doctor, operation=Operation.LIST, resource_type=ResourceType.VISIT, db=db,
    ))
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail)
    # Doctor can only see visits for hospitals they are affiliated with (active)
    affiliations = db.query(HospitalStaff).filter(
        HospitalStaff.user_id == current_doctor.id,
        HospitalStaff.is_active == True
    ).all()
    hospital_ids = [aff.hospital_id for aff in affiliations]
    
    if not hospital_ids:
        return []

    visits = db.query(Visit).filter(Visit.hospital_id.in_(hospital_ids)).all()
    return visits

