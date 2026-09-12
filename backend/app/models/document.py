from sqlalchemy import CheckConstraint, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class DocumentType(str, enum.Enum):
    PRESCRIPTION = "prescription"
    MEDICINE_REPORT = "medicine report"
    LAB_REPORT = "lab report"
    SCAN_REPORT = "scan report"
    DIAGNOSIS_REPORT = "diagnosis report"
    DISCHARGE_SUMMARY = "discharge summary"
    OTHER = "other medical document"

class MedicalDocument(Base):
    __tablename__ = "medical_documents"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_medical_documents_file_size"),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    uploaded_by_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    visit_id = Column(Integer, ForeignKey("visits.id"), nullable=False, index=True)
    
    document_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    
    original_filename = Column(String, nullable=False)
    stored_filename = Column(String, nullable=False, unique=True)
    mime_type = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    checksum = Column(String, nullable=True)
    # Only "clean" is releasable. pending, malicious, scan_error, and any
    # unrecognized value remain quarantined by the download enforcement path.
    scan_status = Column(String, server_default="pending", nullable=False)
    
    status = Column(String, default="active") # active, archived
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    hospital = relationship("Hospital")
    uploaded_by_doctor = relationship("User", foreign_keys=[uploaded_by_doctor_id])
    visit = relationship("Visit")
