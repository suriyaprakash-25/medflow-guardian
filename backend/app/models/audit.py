from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    actor_role = Column(String, nullable=False)
    
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    action = Column(String, nullable=False)
    
    document_id = Column(Integer, ForeignKey("medical_documents.id"), nullable=True)
    access_request_id = Column(Integer, ForeignKey("document_access_requests.id"), nullable=True)
    access_grant_id = Column(Integer, ForeignKey("document_access_grants.id"), nullable=True)
    
    status = Column(String, default="success") # success, failure
    metadata_json = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    actor = relationship("User", foreign_keys=[actor_id])
