from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.triage import TriageRequest
from app.models.user import User
from app.schemas.triage import TriageRequest as TriageRequestSchema, TriageRequestCreate, TriageRequestUpdate
from app.api.dependencies import get_current_patient, get_current_doctor
from app.ai.triage_engine import analyze_symptoms
from app.api.websockets import manager

router = APIRouter()

@router.post("/", response_model=TriageRequestSchema)
async def submit_triage_request(
    request_in: TriageRequestCreate,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    # Analyze symptoms using the mock AI engine
    ai_result = analyze_symptoms(request_in.symptoms)
    
    # Create the db record
    db_request = TriageRequest(
        patient_id=current_patient.id,
        symptoms=request_in.symptoms,
        priority=ai_result["priority"],
        ai_reasoning=ai_result["ai_reasoning"],
        disclaimer=ai_result.get("disclaimer"),
        status="pending"
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)

    await manager.broadcast_to_role({
        "type": "triage_update",
        "data": {
            "id": db_request.id,
            "patient_id": db_request.patient_id,
            "patient_name": current_patient.full_name,
            "status": db_request.status,
            "priority": db_request.priority,
            "symptoms": db_request.symptoms,
            "ai_reasoning": db_request.ai_reasoning,
            "disclaimer": db_request.disclaimer,
            "created_at": db_request.created_at.isoformat()
        }
    }, "doctor")

    return db_request

@router.get("/", response_model=List[TriageRequestSchema])
def list_triage_requests(
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor),
    status: str = None
):
    query = db.query(TriageRequest)
    if status:
        query = query.filter(TriageRequest.status == status)
    
    return query.order_by(TriageRequest.created_at.desc()).all()

@router.get("/patient", response_model=List[TriageRequestSchema])
def list_patient_triage_requests(
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    query = db.query(TriageRequest).filter(TriageRequest.patient_id == current_patient.id)
    return query.order_by(TriageRequest.created_at.desc()).all()

@router.patch("/{id}/status", response_model=TriageRequestSchema)
async def update_triage_status(
    id: int,
    request_in: TriageRequestUpdate,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor)
):
    db_request = db.query(TriageRequest).filter(TriageRequest.id == id).first()
    if not db_request:
        raise HTTPException(status_code=404, detail="Triage request not found")
    
    db_request.status = request_in.status
    db.commit()
    db.refresh(db_request)

    payload = {
        "type": "triage_update",
        "data": {
            "id": db_request.id,
            "status": db_request.status
        }
    }
    await manager.send_personal_message(payload, db_request.patient_id)
    await manager.broadcast_to_role(payload, "doctor")

    return db_request
