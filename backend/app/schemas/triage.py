from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class TriageRequestBase(BaseModel):
    hospital_id: int
    symptoms: str

class TriageRequestCreate(TriageRequestBase):
    pass

class TriageRequestUpdate(BaseModel):
    status: str

class TriageRequest(TriageRequestBase):
    id: int
    patient_id: int
    status: str
    priority: Optional[str] = None
    ai_reasoning: Optional[str] = None
    disclaimer: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
