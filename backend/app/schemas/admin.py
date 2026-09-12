from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal

StaffRole = Literal["admin", "doctor", "staff"]


class HospitalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    contact_info: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = True


class HospitalUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    address: Optional[str] = Field(default=None, max_length=500)
    contact_info: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class StaffCreate(BaseModel):
    email: EmailStr
    role: StaffRole = "doctor"
    password: Optional[str] = Field(default=None, min_length=12, max_length=128)
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=200)


class StaffUpdate(BaseModel):
    role: Optional[StaffRole] = None
    is_active: Optional[bool] = None
