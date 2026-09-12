from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.core.database import get_db
from app.models.hospital import Visit
from app.models.user import User
from app.schemas.clinical import VisitResponse
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType
from pydantic import BaseModel

router = APIRouter()

class VisitCreate(BaseModel):
    patient_id: int
    doctor_id: int
    hospital_id: int
    visit_date: datetime
    reason: str

@router.post("/visits", response_model=VisitResponse)
def create_visit(
    visit_data: VisitCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.VISIT,
        db=db,
        patient_id=visit_data.patient_id,
        hospital_id=visit_data.hospital_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    visit = Visit(
        patient_id=visit_data.patient_id,
        doctor_id=visit_data.doctor_id,
        hospital_id=visit_data.hospital_id,
        visit_date=visit_data.visit_date,
        reason=visit_data.reason,
        status="completed"
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit

@router.get("/visits/patient/{patient_id}", response_model=List[VisitResponse])
def get_patient_visits(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.VISIT,
        db=db,
        patient_id=patient_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    return db.query(Visit).filter(Visit.patient_id == patient_id).order_by(Visit.visit_date.desc()).all()
