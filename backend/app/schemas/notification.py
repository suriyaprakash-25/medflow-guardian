from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class NotificationSchema(BaseModel):
    id: int
    user_id: int
    type: str
    message: str
    is_read: bool
    related_document_id: Optional[int] = None
    related_request_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AuditLogSchema(BaseModel):
    id: int
    actor_id: int
    actor_role: str
    hospital_id: Optional[int] = None
    patient_id: Optional[int] = None
    action: str
    document_id: Optional[int] = None
    access_request_id: Optional[int] = None
    access_grant_id: Optional[int] = None
    status: str
    metadata_json: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
