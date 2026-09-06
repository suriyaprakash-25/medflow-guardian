from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PatientReadingBase(BaseModel):
    heart_rate: int
    oxygen_level: int
    blood_pressure_sys: int
    blood_pressure_dia: int
    is_simulated: bool = True

class PatientReadingCreate(PatientReadingBase):
    pass

class PatientReading(PatientReadingBase):
    id: int
    patient_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class MessageBase(BaseModel):
    receiver_id: int
    content: str

class MessageCreate(MessageBase):
    pass

class Message(MessageBase):
    id: int
    sender_id: int
    created_at: datetime

    class Config:
        from_attributes = True
