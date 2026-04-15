from datetime import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Trip(Base):
    __tablename__ = 'trips'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    title = Column(String(20), nullable=False)
    city_id = Column(Integer, ForeignKey("city.id"), nullable=True)
    privacy_id = Column(Integer, ForeignKey("privacy.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    user = relationship("User")
    city = relationship("City") 