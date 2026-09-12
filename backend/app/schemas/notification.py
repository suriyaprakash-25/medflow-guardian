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
    organization_id: Optional[int] = None
    patient_id: Optional[int] = None
    
    operation: str
    resource_type: str
    resource_id: Optional[str] = None
    
    purpose: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    
    authorization_id: Optional[str] = None
    consent_id: Optional[int] = None
    consent_state_id: Optional[int] = None
    policy_version: Optional[int] = None
    
    enforcement_point: Optional[str] = None
    enforcement_state: Optional[str] = None
    decision: str
    denial_reason: Optional[str] = None
    
    metadata_json: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True
