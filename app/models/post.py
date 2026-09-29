from datetime import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

class Post(Base):
    __tablename__ = 'posts'

    id         = Column(Integer, primary_key=True)
    stop_id    = Column(Integer, ForeignKey("stops.id"), nullable=False)
    title      = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    stop    = relationship("Stop", back_populates="posts")
    images  = relationship("Image", back_populates="post", cascade="all, delete-orphan")
    videos  = relationship("Video", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")

    @property
    def trip_id(self):
        return self.stop.trip_id if self.stop else None

    @property
    def trip_title(self):
        return self.stop.trip.title if self.stop and self.stop.trip else None

    @property
    def lat(self):
        return self.stop.city.lat if self.stop and self.stop.city else None

    @property
    def long(self):
        return self.stop.city.long if self.stop and self.stop.city else None