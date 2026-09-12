from pydantic import BaseModel, EmailStr
from typing import Optional

class HospitalCreate(BaseModel):
    name: str
    address: Optional[str] = None
    contact_info: Optional[str] = None
    is_active: bool = True

class HospitalUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    contact_info: Optional[str] = None
    is_active: Optional[bool] = None

class StaffCreate(BaseModel):
    email: EmailStr
    role: str = "doctor" # "admin", "doctor", "staff"

class StaffUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
