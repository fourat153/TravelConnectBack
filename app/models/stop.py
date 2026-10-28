from datetime import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey,UniqueConstraint
from app.models.post import Post
from sqlalchemy.orm import relationship

class Stop(Base):
    __tablename__ = 'stops'

    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    city_id = Column(Integer, ForeignKey("city.id"), nullable=False)
    title = Column(String, nullable=True)
    description = Column(String, nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    trip = relationship("Trip", back_populates="stops")
    city = relationship("City")
    posts = relationship("Post", back_populates="stop", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("trip_id", "order", name="uq_trip_stop_order"),
    )