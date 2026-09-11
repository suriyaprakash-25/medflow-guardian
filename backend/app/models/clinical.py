from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Medication(Base):
    __tablename__ = "medications"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    medication_id = Column(Integer, ForeignKey("medications.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    
    dosage = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    medication = relationship("Medication")
    hospital = relationship("Hospital")

class LabResult(Base):
    __tablename__ = "lab_results"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    
    test_name = Column(String, nullable=False)
    result_value = Column(String, nullable=False)
    unit = Column(String, nullable=True)
    reference_range = Column(String, nullable=True)
    status = Column(String, default="completed") # pending, completed, cancelled
    test_date = Column(DateTime(timezone=True), nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    hospital = relationship("Hospital")

class ClinicalNote(Base):
    __tablename__ = "clinical_notes"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False)
    
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String, default="general") # e.g. general, consultation, progress, discharge
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    hospital = relationship("Hospital")
