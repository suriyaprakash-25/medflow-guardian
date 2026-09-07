from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    
    is_read = Column(Boolean, default=False)
    
    related_document_id = Column(Integer, ForeignKey("medical_documents.id"), nullable=True)
    related_request_id = Column(Integer, ForeignKey("document_access_requests.id"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
