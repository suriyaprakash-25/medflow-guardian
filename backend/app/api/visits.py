from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import get_patient_identity, get_practitioner_identity
from app.core.database import get_db
from app.models.hospital import Visit
from app.models.user import User
from app.schemas.clinical import VisitResponse
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)

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
    current_doctor: User = Depends(get_practitioner_identity),
):
    """Create a visit only for the authenticated practitioner.

    Visit creation establishes the care relationship used by later protected
    workflows, so it is explicitly pre-consent but still organization-bound and
    actor-bound. A client cannot nominate another practitioner in the payload.
    """
    if visit_data.doctor_id != current_doctor.id:
        raise HTTPException(
            status_code=403,
            detail="A practitioner may only create visits assigned to themselves",
        )

    patient = (
        db.query(User)
        .filter(
            User.id == visit_data.patient_id,
            User.role == "patient",
            User.is_active == True,
        )
        .first()
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="Active patient not found")

    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_doctor,
        operation=Operation.CREATE,
        resource_type=ResourceType.VISIT,
        db=db,
        patient_id=patient.id,
        hospital_id=visit_data.hospital_id,
        relationship_context=current_doctor.id,
        requires_consent=False,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    visit = Visit(
        patient_id=patient.id,
        doctor_id=current_doctor.id,
        hospital_id=visit_data.hospital_id,
        date=visit_data.visit_date,
        reason=visit_data.reason,
        status="completed",
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return visit


@router.get("/visits/patient/{patient_id}", response_model=List[VisitResponse])
def get_patient_visits(
    patient_id: int,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient_identity),
):
    """Return visit history only to the patient who owns that history.

    This endpoint is intentionally patient-owned. Practitioner access to patient
    history must use a separately scoped, consent-aware workflow rather than an
    arbitrary patient ID supplied in the URL.
    """
    if patient_id != current_patient.id:
        raise HTTPException(status_code=403, detail="Cannot access another patient's visits")

    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_patient,
        operation=Operation.LIST,
        resource_type=ResourceType.VISIT,
        db=db,
        patient_id=current_patient.id,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    # Defense in depth: scope by the authenticated identity, never the path value.
    return (
        db.query(Visit)
        .filter(Visit.patient_id == current_patient.id)
        .order_by(Visit.date.desc())
        .all()
    )
