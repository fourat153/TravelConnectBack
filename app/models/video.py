
from datetime import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey
from sqlalchemy.orm import relationship


class Video(Base):
    __tablename__ = 'video'

    id      = Column(Integer, primary_key=True)
    link    = Column(String, nullable=False)
    caption = Column(String, nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)

    post = relationship("Post", back_populates="videos")
