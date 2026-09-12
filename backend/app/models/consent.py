from sqlalchemy import CheckConstraint, Column, Integer, String, DateTime, ForeignKey, JSON, UniqueConstraint
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
    """
    High-level governance entity representing a patient's consent decision.
    """
    __tablename__ = "consents"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "source_resource_id",
            name="uq_consents_source_system_resource_id",
        ),
        CheckConstraint(
            "(source_system IS NULL) = (source_resource_id IS NULL)",
            name="ck_consents_provenance_pair",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'suspended', 'revoked', 'expired', 'superseded', 'cancelled')",
            name="ck_consents_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Optional context mapping if consent is explicitly tied to an actor/hospital
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True, index=True)
    
    status = Column(String, default=ConsentStatus.DRAFT.value, nullable=False)

    # Stable provenance for imported FHIR resources. Both values are null for
    # consents authored natively in MedFlow.
    source_system = Column(String(255), nullable=True)
    source_resource_id = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("User", foreign_keys=[patient_id])
    doctor = relationship("User", foreign_keys=[doctor_id])
    hospital = relationship("Hospital", foreign_keys=[hospital_id])
    
    policy_versions = relationship("ConsentPolicyVersion", back_populates="consent", cascade="all, delete-orphan")
    state_history = relationship("ConsentState", back_populates="consent", cascade="all, delete-orphan", order_by="ConsentState.created_at")

class ConsentPolicyVersion(Base):
    """
    Immutable policy ruleset attached to a Consent.
    """
    __tablename__ = "consent_policy_versions"
    __table_args__ = (
        UniqueConstraint(
            "consent_id",
            "version_number",
            name="uq_consent_policy_versions_consent_version",
        ),
        CheckConstraint("version_number > 0", name="ck_consent_policy_version_positive"),
        CheckConstraint(
            "status IN ('active', 'superseded')",
            name="ck_consent_policy_versions_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=False, index=True)
    
    version_number = Column(Integer, nullable=False)
    
    # Immutable policy payload
    # Expected schema: { "allowed_purposes": ["TREATMENT"], "allowed_operations": ["read", "download"] }
    policy_payload = Column(JSON, nullable=False)
    
    status = Column(String, default="active", nullable=False) # active, superseded
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    consent = relationship("Consent", back_populates="policy_versions")
    states = relationship("ConsentState", back_populates="policy_version")

class ConsentState(Base):
    """
    Append-only log of chronological state transitions.
    The most recent row for a given consent_id is its Authoritative Consent State.
    """
    __tablename__ = "consent_states"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'suspended', 'revoked', 'expired', 'superseded', 'cancelled')",
            name="ck_consent_states_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    consent_id = Column(Integer, ForeignKey("consents.id"), nullable=False, index=True)
    policy_version_id = Column(Integer, ForeignKey("consent_policy_versions.id"), nullable=False, index=True)
    
    status = Column(String, nullable=False) # matches ConsentStatus
    reason = Column(String(500), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    consent = relationship("Consent", back_populates="state_history")
    policy_version = relationship("ConsentPolicyVersion", back_populates="states")
