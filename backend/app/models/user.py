from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    phone_number = Column(String, nullable=True)
    role = Column(String, nullable=False) # "doctor" or "patient"
    is_active = Column(Boolean, default=True)

    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False, foreign_keys="PatientProfile.user_id")
    practitioner_profile = relationship("PractitionerProfile", back_populates="user", uselist=False, foreign_keys="PractitionerProfile.user_id")
    assigned_patients = relationship("PatientProfile", back_populates="assigned_doctor", foreign_keys="PatientProfile.assigned_doctor_id")
    triage_requests = relationship("TriageRequest", back_populates="patient", foreign_keys="TriageRequest.patient_id")
    
    # New relationships for Multi-Hospital structure
    hospital_affiliations = relationship("HospitalStaff", back_populates="user", cascade="all, delete-orphan")
    visits_as_patient = relationship("Visit", back_populates="patient", foreign_keys="Visit.patient_id", cascade="all, delete-orphan")
    visits_as_doctor = relationship("Visit", back_populates="doctor", foreign_keys="Visit.doctor_id")

class PractitionerProfile(Base):
    __tablename__ = "practitioner_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialty = Column(String, nullable=True)
    license_number = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)

    user = relationship("User", back_populates="practitioner_profile", foreign_keys=[user_id])

class PatientProfile(Base):
    __tablename__ = "patient_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    medical_history = Column(String, nullable=True)
    
    # New demographic & emergency fields
    date_of_birth = Column(String, nullable=True) # ISO format YYYY-MM-DD
    address = Column(String, nullable=True)
    emergency_contact_name = Column(String, nullable=True)
    emergency_contact_phone = Column(String, nullable=True)
    blood_type = Column(String, nullable=True)
    allergies = Column(String, nullable=True)

    user = relationship("User", back_populates="patient_profile", foreign_keys=[user_id])
    assigned_doctor = relationship("User", back_populates="assigned_patients", foreign_keys=[assigned_doctor_id])
