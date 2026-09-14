from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, model_validator

from app.core.time import as_utc
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
    expires_at: datetime
    responded_at: Optional[datetime] = None
    requested_documents: List[MedicalDocumentSchema] = []

    @model_validator(mode="after")
    def expose_effective_expiry(self):
        if (
            self.status == "pending"
            and self.expires_at is not None
            and as_utc(self.expires_at) <= datetime.now(timezone.utc)
        ):
            self.status = "expired"
        return self

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
