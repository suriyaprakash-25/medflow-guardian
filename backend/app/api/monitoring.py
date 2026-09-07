from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.monitoring import PatientReading, Message
from app.models.user import User
from app.schemas.monitoring import PatientReadingCreate, PatientReading as PatientReadingSchema
from app.schemas.monitoring import MessageCreate, Message as MessageSchema
from app.api.dependencies import get_current_patient, get_current_doctor, get_current_user
from app.models.hospital import Visit
from app.api.websockets import manager

router = APIRouter()

@router.post("/readings", response_model=PatientReadingSchema)
async def submit_reading(
    reading_in: PatientReadingCreate,
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    db_reading = PatientReading(
        patient_id=current_patient.id,
        heart_rate=reading_in.heart_rate,
        oxygen_level=reading_in.oxygen_level,
        blood_pressure_sys=reading_in.blood_pressure_sys,
        blood_pressure_dia=reading_in.blood_pressure_dia,
        is_simulated=reading_in.is_simulated
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)

    # Broadcast reading to doctors
    await manager.broadcast_to_role({
        "type": "reading",
        "data": {
            "patient_id": current_patient.id,
            "patient_name": current_patient.full_name,
            "heart_rate": db_reading.heart_rate,
            "oxygen_level": db_reading.oxygen_level,
            "blood_pressure": f"{db_reading.blood_pressure_sys}/{db_reading.blood_pressure_dia}",
            "is_simulated": db_reading.is_simulated,
            "created_at": db_reading.created_at.isoformat()
        }
    }, "doctor")

    return db_reading

@router.get("/readings/{patient_id}", response_model=List[PatientReadingSchema])
def get_readings(
    patient_id: int,
    db: Session = Depends(get_db),
    current_doctor: User = Depends(get_current_doctor)
):
    # Verify relationship
    visit = db.query(Visit).filter(
        Visit.patient_id == patient_id,
        Visit.doctor_id == current_doctor.id
    ).first()
    if not visit:
        raise HTTPException(status_code=403, detail="Not authorized to view readings for this patient")

    return db.query(PatientReading).filter(PatientReading.patient_id == patient_id).order_by(PatientReading.created_at.desc()).limit(50).all()

@router.get("/readings/patient", response_model=List[PatientReadingSchema])
def get_patient_own_readings(
    db: Session = Depends(get_db),
    current_patient: User = Depends(get_current_patient)
):
    return db.query(PatientReading).filter(PatientReading.patient_id == current_patient.id).order_by(PatientReading.created_at.desc()).limit(50).all()

@router.post("/messages", response_model=MessageSchema)
async def send_message(
    msg_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify they have a relationship
    if current_user.role == "patient":
        visit = db.query(Visit).filter(Visit.patient_id == current_user.id, Visit.doctor_id == msg_in.receiver_id).first()
    else:
        visit = db.query(Visit).filter(Visit.patient_id == msg_in.receiver_id, Visit.doctor_id == current_user.id).first()

    if not visit:
        raise HTTPException(status_code=403, detail="Not authorized to message this user")

    db_msg = Message(
        sender_id=current_user.id,
        receiver_id=msg_in.receiver_id,
        content=msg_in.content
    )
    db.add(db_msg)
    db.commit()
    db.refresh(db_msg)

    # Broadcast to the receiver
    await manager.send_personal_message({
        "type": "message",
        "data": {
            "id": db_msg.id,
            "sender_id": db_msg.sender_id,
            "receiver_id": db_msg.receiver_id,
            "content": db_msg.content,
            "created_at": db_msg.created_at.isoformat()
        }
    }, msg_in.receiver_id)

    return db_msg

@router.get("/messages/{user_id}", response_model=List[MessageSchema])
def get_messages(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Verify relationship
    if current_user.role == "patient":
        visit = db.query(Visit).filter(Visit.patient_id == current_user.id, Visit.doctor_id == user_id).first()
    else:
        visit = db.query(Visit).filter(Visit.patient_id == user_id, Visit.doctor_id == current_user.id).first()

    if not visit:
        raise HTTPException(status_code=403, detail="Not authorized to view messages with this user")

    # Fetch chat history between current_user and user_id
    messages = db.query(Message).filter(
        ((Message.sender_id == current_user.id) & (Message.receiver_id == user_id)) |
        ((Message.sender_id == user_id) & (Message.receiver_id == current_user.id))
    ).order_by(Message.created_at.asc()).all()
    return messages
