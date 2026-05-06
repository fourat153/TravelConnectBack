from sqlalchemy import Column, Integer, String, DateTime, Enum, ForeignKey
from app.enums import PrivacyType
from .base import Base


class Privacy(Base):
    __tablename__ = "privacy"

    id = Column(Integer, primary_key=True)
    name = Column(Enum(PrivacyType), nullable=False , unique=True)
