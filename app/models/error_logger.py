import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, func

class ErrorLogger(Base):
    __tablename__ = "error_logger"

    id = Column(Integer, primary_key=True)
    orig = Column(String, nullable=True)
    statement = Column(String, nullable=True)
    params = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)