from typing import Dict, List, Set

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_authorization_service,
    get_current_user,
    get_patient_identity,
)
from app.core.database import get_db
from app.models.hospital import Appointment
from app.models.user import User
from app.schemas.clinical import (
    AppointmentCreate,
    AppointmentResponse,
    AppointmentStatus,
    AppointmentUpdate,
)
from app.services.authorization import (
    AuthorizationContext,
    AuthorizationService,
    Operation,
    ResourceType,
)

router = APIRouter()

_PATIENT_TRANSITIONS: Dict[str, Set[str]] = {
    AppointmentStatus.SCHEDULED.value: {AppointmentStatus.CANCELLED.value},
    AppointmentStatus.CONFIRMED.value: {AppointmentStatus.CANCELLED.value},
}

_DOCTOR_TRANSITIONS: Dict[str, Set[str]] = {
    AppointmentStatus.SCHEDULED.value: {
        AppointmentStatus.CONFIRMED.value,
        AppointmentStatus.CANCELLED.value,
    },
    AppointmentStatus.CONFIRMED.value: {
        AppointmentStatus.COMPLETED.value,
        AppointmentStatus.CANCELLED.value,
    },
}


def _enforce_status_transition(*, actor_role: str, current_status: str, new_status: str) -> None:
    if new_status == current_status:
        return

    transitions = (
        _PATIENT_TRANSITIONS if actor_role == "patient" else _DOCTOR_TRANSITIONS
        if actor_role == "doctor" else {}
    )
    if new_status not in transitions.get(current_status, set()):
        raise HTTPException(
            status_code=409,
            detail=(
                f"Appointment transition '{current_status}' -> '{new_status}' "
                f"is not permitted for role '{actor_role}'"
            ),
        )


@router.post("/appointments", response_model=AppointmentResponse)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    auth_svc = AuthorizationService(db)
    # The CAE ensures only a patient creates an appointment for themselves.
    ctx = AuthorizationContext(
        actor=current_user,
        operation=Operation.CREATE,
        resource_type=ResourceType.APPOINTMENT,
        db=db,
        hospital_id=appointment_data.hospital_id,
        patient_id=current_user.id if current_user.role == "patient" else None,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    appointment = Appointment(
        patient_id=current_user.id,
        doctor_id=appointment_data.doctor_id,
        hospital_id=appointment_data.hospital_id,
        scheduled_time=appointment_data.scheduled_time,
        reason=appointment_data.reason,
        notes=appointment_data.notes,
        status=AppointmentStatus.SCHEDULED.value,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


@router.get("/appointments/patient/{patient_id}", response_model=List[AppointmentResponse])
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient_identity),
):
    """Return appointment history only to the patient who owns it."""
    if patient_id != current_patient.id:
        raise HTTPException(status_code=403, detail="Cannot access another patient's appointments")

    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_patient,
        operation=Operation.LIST,
        resource_type=ResourceType.APPOINTMENT,
        db=db,
        patient_id=current_patient.id,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    return (
        db.query(Appointment)
        .filter(Appointment.patient_id == current_patient.id)
        .order_by(Appointment.scheduled_time.desc())
        .all()
    )


@router.get("/appointments/patient", response_model=List[AppointmentResponse])
def get_my_appointments(
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_patient_identity),
):
    auth_svc = AuthorizationService(db)
    ctx = AuthorizationContext(
        actor=current_patient,
        operation=Operation.LIST,
        resource_type=ResourceType.APPOINTMENT,
        db=db,
        patient_id=current_patient.id,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    return (
        db.query(Appointment)
        .filter(Appointment.patient_id == current_patient.id)
        .order_by(Appointment.scheduled_time.desc())
        .all()
    )


@router.get("/appointments/doctor/{doctor_id}", response_model=List[AppointmentResponse])
def get_doctor_appointments(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    auth_svc: AuthorizationService = Depends(get_authorization_service),
):
    decision = auth_svc.authorize(
        AuthorizationContext(
            actor=current_user,
            operation=Operation.LIST,
            resource_type=ResourceType.APPOINTMENT,
            db=db,
            relationship_context=doctor_id,
        )
    )
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)
    return (
        db.query(Appointment)
        .filter(Appointment.doctor_id == current_user.id)
        .order_by(Appointment.scheduled_time.desc())
        .all()
    )


@router.patch("/appointments/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    update_data: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
        resource=appointment,
        patient_id=appointment.patient_id,
        hospital_id=appointment.hospital_id,
        # Scheduling/status management is operational workflow, not disclosure
        # of patient content. The base CAE ownership/membership checks remain
        # mandatory, but this operation does not require consent policy context.
        requires_consent=False,
    )
    decision = auth_svc.authorize(ctx)
    if not decision.allowed:
        raise HTTPException(status_code=403, detail=decision.detail or decision.reason)

    if current_user.role == "patient" and update_data.notes is not None:
        raise HTTPException(
            status_code=403,
            detail="Patients cannot modify practitioner appointment notes",
        )

    if update_data.status is not None:
        new_status = update_data.status.value
        _enforce_status_transition(
            actor_role=current_user.role,
            current_status=appointment.status,
            new_status=new_status,
        )
        appointment.status = new_status

    if update_data.notes is not None and current_user.role == "doctor":
        appointment.notes = update_data.notes

    db.commit()
    db.refresh(appointment)
    return appointment
