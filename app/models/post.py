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
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("PostLike", back_populates="post", cascade="all, delete-orphan")