from datetime import datetime
from .base import Base
from sqlalchemy import Column, Integer, String, Enum as SAEnum
from app.enums import PrivacyEntityType, PrivacyType

class PrivacySettings(Base):
    __tablename__ = 'privacy_settings'

    id          = Column(Integer, primary_key=True)
    entity_type = Column(SAEnum(PrivacyEntityType), nullable=False)
    entity_id   = Column(Integer, nullable=False)
    privacy_type = Column(SAEnum(PrivacyType), nullable=False, default=PrivacyType.public)