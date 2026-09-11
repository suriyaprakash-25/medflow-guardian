from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class AppointmentBase(BaseModel):
    hospital_id: int
    doctor_id: int
    scheduled_time: datetime
    reason: Optional[str] = None
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
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
    visit_date: datetime
    reason: str
    status: str
    created_at: datetime
    class Config:
        from_attributes = True
