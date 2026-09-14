from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class OIDCIdentity(Base):
    """Immutable external OIDC subject binding to an existing MedFlow user."""

    __tablename__ = "oidc_identities"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "issuer",
            "subject",
            name="uq_oidc_identity_provider_issuer_subject",
        ),
        UniqueConstraint(
            "user_id",
            "provider",
            "issuer",
            name="uq_oidc_identity_user_provider_issuer",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False)
    issuer = Column(String(512), nullable=False)
    subject = Column(String(512), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User")
