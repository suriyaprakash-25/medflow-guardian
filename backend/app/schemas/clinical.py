from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class AppointmentBase(BaseModel):
    hospital_id: int
    doctor_id: int
    scheduled_time: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = None


class AppointmentResponse(AppointmentBase):
    id: int
    patient_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class MedicationResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionCreate(BaseModel):
    patient_id: int
    medication_id: int
    hospital_id: int
    dosage: str
    frequency: str
    start_date: datetime
    end_date: Optional[datetime] = None
    notes: Optional[str] = None


class PrescriptionResponse(PrescriptionCreate):
    id: int
    doctor_id: int
    is_active: bool
    created_at: datetime
    medication: Optional[MedicationResponse] = None

    class Config:
        from_attributes = True


class LabResultCreate(BaseModel):
    patient_id: int
    hospital_id: int
    test_name: str
    result_value: str
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    test_date: datetime
    notes: Optional[str] = None


class LabResultResponse(LabResultCreate):
    id: int
    doctor_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClinicalNoteCreate(BaseModel):
    patient_id: int
    hospital_id: int
    title: str
    content: str
    note_type: str = "general"


class ClinicalNoteResponse(ClinicalNoteCreate):
    id: int
    doctor_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class VisitResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    hospital_id: int
    # The database column is historically named `date`; keep the public API
    # contract as `visit_date` without introducing a schema migration solely for
    # serialization.
    visit_date: datetime = Field(validation_alias="date")
    reason: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True
