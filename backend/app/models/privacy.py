from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.sql import func

from app.core.database import Base


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"
    __table_args__ = (
        CheckConstraint(
            "request_type IN ('export', 'deletion')",
            name="ck_privacy_requests_type",
        ),
        Index(
            "uq_privacy_requests_active_type",
            "patient_id",
            "request_type",
            unique=True,
            postgresql_where=text("status IN ('pending', 'approved')"),
        ),
        CheckConstraint(
            "status IN ('pending', 'approved', 'rejected', 'completed')",
            name="ck_privacy_requests_status",
        ),
    )

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    request_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="pending", index=True)
    reason = Column(Text, nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class PrivacyLegalHold(Base):
    __tablename__ = "privacy_legal_holds"
    __table_args__ = (
        Index(
            "uq_privacy_legal_holds_active_patient",
            "patient_id",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(Text, nullable=False)
    active = Column(Boolean, nullable=False, default=True, index=True)
    placed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    released_by_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    placed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
