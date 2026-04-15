from sqlalchemy import Column, Integer, ForeignKey, Enum
from sqlalchemy.orm import relationship
from .base import Base
from app.enums import PrivacyEntityType


class PrivacySettings(Base):
    __tablename__ = "privacy_settings"

    id = Column(Integer, primary_key=True)
    entity_type = Column(Enum(PrivacyEntityType), nullable=False) 
    entity_id = Column(Integer, nullable=False)
    privacy_type = Column(Integer, ForeignKey("privacy.id"), nullable=False)

    privacy = relationship("Privacy")