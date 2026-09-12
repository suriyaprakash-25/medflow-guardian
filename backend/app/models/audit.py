from sqlalchemy import CheckConstraint, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint("decision IN ('ALLOW', 'DENY')", name="ck_audit_logs_decision"),
    )

    id = Column(Integer, primary_key=True, index=True)
    
    # Who
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    actor_role = Column(String, nullable=False)
    organization_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    # What
    operation = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String, nullable=True, index=True)
    
    # Security Context
    purpose = Column(String, nullable=True)
    request_id = Column(String, nullable=True, index=True)
    correlation_id = Column(String, nullable=True, index=True)
    
    # Authorization & Consent Trace
    authorization_id = Column(String, nullable=True)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=True, index=True)
    consent_state_id = Column(Integer, ForeignKey("consent_states.id"), nullable=True, index=True)
    policy_version = Column(Integer, nullable=True)
    
    # Enforcement
    enforcement_point = Column(String, nullable=True)
    enforcement_state = Column(String, nullable=True)
    decision = Column(String, nullable=False) # 'ALLOW' or 'DENY'
    denial_reason = Column(String, nullable=True)
    
    # Additional Context
    metadata_json = Column(Text, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    actor = relationship("User", foreign_keys=[actor_id])
