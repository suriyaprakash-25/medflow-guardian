from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.schemas.document import MedicalDocumentSchema

class AccessRequestCreate(BaseModel):
    patient_id: int
    hospital_id: int
    document_ids: List[int]
    reason: str

class AccessRequestResponse(BaseModel):
    id: int
    patient_id: int
    requesting_doctor_id: int
    requesting_hospital_id: int
    reason: str
    status: str
    requested_at: datetime
    responded_at: Optional[datetime] = None
    requested_documents: List[MedicalDocumentSchema] = []

    class Config:
        from_attributes = True

class AccessRequestApprove(BaseModel):
    duration_hours: int
    document_ids: List[int]

class AccessRequestReject(BaseModel):
    rejection_reason: Optional[str] = None

class AccessGrantResponse(BaseModel):
    id: int
    access_request_id: int
    patient_id: int
    doctor_id: int
    hospital_id: int
    status: str
    granted_at: datetime
    expires_at: datetime
    revoked_at: Optional[datetime] = None
    granted_documents: List[MedicalDocumentSchema] = []

    class Config:
        from_attributes = True
