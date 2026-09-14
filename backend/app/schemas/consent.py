from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class ConsentCreate(BaseModel):
    hospital_id: Optional[int] = None
    doctor_id: Optional[int] = None
    allowed_purposes: List[str] = Field(min_length=1)
    allowed_operations: List[str] = Field(min_length=1)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_period(self):
        _validate_validity_period(self.valid_from, self.valid_until)
        return self

class ConsentTransition(BaseModel):
    target_status: str
    reason: Optional[str] = None

class ConsentPolicyVersionCreate(BaseModel):
    allowed_purposes: List[str] = Field(min_length=1)
    allowed_operations: List[str] = Field(min_length=1)
    reason: Optional[str] = Field(default=None, max_length=500)
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_period(self):
        _validate_validity_period(self.valid_from, self.valid_until)
        return self

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
    current_state: Optional[ConsentStateResponse] = None
    active_policy: Optional["ConsentPolicyVersionResponse"] = None
    
    class Config:
        from_attributes = True

class ConsentPolicyVersionResponse(BaseModel):
    id: int
    consent_id: int
    version_number: int
    policy_payload: Dict[str, Any]
    status: str
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


def _validate_validity_period(
    valid_from: Optional[datetime], valid_until: Optional[datetime]
) -> None:
    for name, value in (("valid_from", valid_from), ("valid_until", valid_until)):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError(f"{name} must include a timezone offset")
    if valid_from is not None and valid_until is not None and valid_until <= valid_from:
        raise ValueError("valid_until must be later than valid_from")


class FHIRConsentImportResponse(BaseModel):
    consent_id: int
    policy_version_id: int
    policy_version_number: int
    state_id: int
    state_status: str
    created: bool
    source_system: str
    source_resource_id: str
    policy_payload: Dict[str, Any]


ConsentResponse.model_rebuild()
