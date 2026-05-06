from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from app.enums import CodeStatus
class ConfirmationCode(Base):
    __tablename__ = "confirmation_code"

    id        = Column(Integer, primary_key=True)
    user_id   = Column(Integer, ForeignKey("user.id"), nullable=False)
    code      = Column(String, nullable=False)   
    email = Column(String, nullable=False)
    status    = Column(Enum(CodeStatus), nullable=False)
    expires_at = Column(DateTime)
    created_at = Column(DateTime)
    user = relationship("User", foreign_keys=[user_id])