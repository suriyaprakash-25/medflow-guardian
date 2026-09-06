from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class TriageRequest(Base):
    __tablename__ = "triage_requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symptoms = Column(Text, nullable=False)
    status = Column(String, default="pending") # pending, reviewed, resolved
    priority = Column(String, nullable=True) # low, medium, high, critical
    ai_reasoning = Column(Text, nullable=True)
    disclaimer = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("User", back_populates="triage_requests", foreign_keys=[patient_id])
