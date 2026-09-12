from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    address = Column(String, nullable=True)
    contact_info = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("HospitalStaff", back_populates="hospital", cascade="all, delete-orphan")
    visits = relationship("Visit", back_populates="hospital", cascade="all, delete-orphan")


class HospitalStaff(Base):
    __tablename__ = "hospital_staff"
    __table_args__ = (UniqueConstraint('user_id', 'hospital_id', name='uq_hospital_staff_user_hospital'),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    role = Column(String, default="doctor") # e.g., admin, doctor, staff
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="hospital_affiliations")
    hospital = relationship("Hospital", back_populates="staff")


class Visit(Base):
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="completed") # scheduled, active, completed, cancelled
    reason = Column(Text, nullable=True)

    patient = relationship("User", foreign_keys=[patient_id], back_populates="visits_as_patient")
    doctor = relationship("User", foreign_keys=[doctor_id], back_populates="visits_as_doctor")
    hospital = relationship("Hospital", back_populates="visits")

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    status = Column(String, default="scheduled") # scheduled, cancelled, completed
    reason = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    hospital = relationship("Hospital")
