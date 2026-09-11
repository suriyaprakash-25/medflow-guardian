from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.hospital import Appointment
from app.models.user import User
from app.schemas.clinical import AppointmentCreate, AppointmentResponse, AppointmentUpdate
from app.api.dependencies import get_current_user
from app.services.authorization import AuthorizationService, AuthorizationContext, Operation, ResourceType

router = APIRouter()

@router.post("/appointments", response_model=AppointmentResponse)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    # The CAE will ensure the patient is creating their own appointment
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.APPOINTMENT,
        db=db,
        hospital_id=appointment_data.hospital_id,
        patient_id=current_user.id if current_user.role == "patient" else appointment_data.patient_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
        
    appointment = Appointment(
        patient_id=ctx.patient_id,
        doctor_id=appointment_data.doctor_id,
        hospital_id=appointment_data.hospital_id,
        scheduled_time=appointment_data.scheduled_time,
        reason=appointment_data.reason,
        notes=appointment_data.notes,
        status="scheduled"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment

@router.get("/appointments/patient/{patient_id}", response_model=List[AppointmentResponse])
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.LIST,
        resource_type=ResourceType.APPOINTMENT,
        db=db,
        patient_id=patient_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)

    return db.query(Appointment).filter(Appointment.patient_id == patient_id).order_by(Appointment.scheduled_time.desc()).all()

@router.get("/appointments/doctor/{doctor_id}", response_model=List[AppointmentResponse])
def get_doctor_appointments(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "doctor" or current_user.id != doctor_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return db.query(Appointment).filter(Appointment.doctor_id == doctor_id).order_by(Appointment.scheduled_time.desc()).all()

@router.patch("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
        
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.UPDATE,
        resource_type=ResourceType.APPOINTMENT,
        db=db,
        patient_id=appointment.patient_id,
        hospital_id=appointment.hospital_id
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.reason)
        
    if update_data.status:
        appointment.status = update_data.status
    if update_data.notes and current_user.role == "doctor":
        appointment.notes = update_data.notes
        
    db.commit()
    db.refresh(appointment)
    return appointment
