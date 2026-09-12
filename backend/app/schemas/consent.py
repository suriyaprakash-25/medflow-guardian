from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ConsentCreate(BaseModel):
    hospital_id: Optional[int] = None
    doctor_id: Optional[int] = None
    allowed_purposes: List[str]
    allowed_operations: List[str]

class ConsentTransition(BaseModel):
    target_status: str
    reason: Optional[str] = None

class ConsentStateResponse(BaseModel):
    id: int
    consent_id: int
    policy_version_id: int
    status: str
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ConsentResponse(BaseModel):
    id: int
    patient_id: int
    hospital_id: Optional[int]
    doctor_id: Optional[int]
    status: str
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
