from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentUploadResponse(BaseModel):
    id: int
    message: str

class MedicalDocumentSchema(BaseModel):
    id: int
    patient_id: int
    hospital_id: int
    uploaded_by_doctor_id: int
    visit_id: int
    
    document_type: str
    title: str
    description: Optional[str] = None
    
    original_filename: str
    mime_type: str
    file_size: int
    
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
