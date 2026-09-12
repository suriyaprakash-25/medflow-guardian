from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class ConsentStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUPERSEDED = "superseded"
    CANCELLED = "cancelled"

class Consent(Base):
    """High-level governance entity representing a patient's consent decision."""
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)
    status = Column(String, default=ConsentStatus.DRAFT.value, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    hospital = relationship("Hospital", foreign_keys=[hospital_id])
    policy_versions = relationship("ConsentPolicyVersion", back_populates="consent", cascade="all, delete-orphan")
    state_history = relationship("ConsentState", back_populates="consent", cascade="all, delete-orphan", order_by="ConsentState.created_at")

class ConsentPolicyVersion(Base):
    """Immutable policy ruleset attached to a Consent."""
    __tablename__ = "consent_policy_versions"

    id = Column(Integer, primary_key=True, index=True)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    policy_payload = Column(JSON, nullable=False)
    status = Column(String, default="active", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    consent = relationship("Consent", back_populates="policy_versions")
    states = relationship("ConsentState", back_populates="policy_version")

class ConsentState(Base):
    """Append-only log of chronological consent state transitions."""
    __tablename__ = "consent_states"

    id = Column(Integer, primary_key=True, index=True)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=False, index=True)
    policy_version_id = Column(Integer, ForeignKey("consent_policy_versions.id"), nullable=False, index=True)
    status = Column(String, nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    consent = relationship("Consent", back_populates="state_history")
    policy_version = relationship("ConsentPolicyVersion", back_populates="states")
