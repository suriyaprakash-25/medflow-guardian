from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class PrivacyRequestCreate(BaseModel):
    request_type: Literal["export", "deletion"]
    reason: str | None = Field(default=None, max_length=2000)


class PrivacyRequestDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    review_notes: str = Field(min_length=1, max_length=4000)


class LegalHoldCreate(BaseModel):
    patient_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=4000)


class PrivacyRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    request_type: str
    status: str
    reason: str | None
    review_notes: str | None
    requested_at: datetime
    reviewed_at: datetime | None
    completed_at: datetime | None
