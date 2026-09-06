from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class PatientProfileBase(BaseModel):
    medical_history: Optional[str] = None

class PatientProfile(PatientProfileBase):
    id: int
    user_id: int
    assigned_doctor_id: Optional[int] = None

    class Config:
        from_attributes = True
