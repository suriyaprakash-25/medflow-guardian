from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class HospitalBase(BaseModel):
    name: str
    address: Optional[str] = None
    contact_info: Optional[str] = None
    is_active: bool = True

class Hospital(HospitalBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class VisitBase(BaseModel):
    hospital_id: int
    doctor_id: Optional[int] = None
    status: str = "scheduled"
    reason: Optional[str] = None

class Visit(VisitBase):
    id: int
    patient_id: int
    date: datetime

    class Config:
        from_attributes = True

class VisitWithDetails(Visit):
    hospital: Hospital
    # patient and doctor could be added later if needed
    
    class Config:
        from_attributes = True
