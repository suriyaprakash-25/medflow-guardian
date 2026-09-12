from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

access_request_documents = Table(
    'access_request_documents',
    Base.metadata,
    Column('access_request_id', Integer, ForeignKey('document_access_requests.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('medical_documents.id'), primary_key=True)
)

access_grant_documents = Table(
    'access_grant_documents',
    Base.metadata,
    Column('access_grant_id', Integer, ForeignKey('document_access_grants.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('medical_documents.id'), primary_key=True)
)

class DocumentAccessRequest(Base):
    __tablename__ = "document_access_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requesting_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    requesting_hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    
    reason = Column(Text, nullable=False)
    status = Column(String, default="pending") # pending, approved, rejected, cancelled, expired
    
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    responded_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)

    patient = relationship("User", foreign_keys=[patient_id])
    requesting_doctor = relationship("User", foreign_keys=[requesting_doctor_id])
    requesting_hospital = relationship("Hospital")
    
    # The documents the doctor is requesting access to (could be empty meaning 'all available' or explicit)
    requested_documents = relationship("MedicalDocument", secondary=access_request_documents)
    
    grant = relationship("DocumentAccessGrant", back_populates="request", uselist=False)

class DocumentAccessGrant(Base):
    __tablename__ = "document_access_grants"

    id = Column(Integer, primary_key=True, index=True)
    access_request_id = Column(Integer, ForeignKey("document_access_requests.id"), nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=False, index=True)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=True, index=True) # Phase 5: Nullable initially for migration, then should be strict
    
    status = Column(String, default="active") # active, revoked, expired
    
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    request = relationship("DocumentAccessRequest", back_populates="grant")
    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    hospital = relationship("Hospital")
    consent = relationship("Consent")
    
    granted_documents = relationship("MedicalDocument", secondary=access_grant_documents)
