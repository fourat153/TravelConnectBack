from sqlalchemy import Column, Integer, String
from .base import Base


class Privacy(Base):
    __tablename__ = "privacy"

    id = Column(Integer, primary_key=True)
    name = Column(String(20), nullable=False, unique=True)