
from datetime import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey , Enum
from sqlalchemy.orm import relationship
from app.enums import FriendshipStatusEnum



class FriendshipStatus(Base):
    __tablename__ = "friendship_status"

    id   = Column(Integer, primary_key=True)
    name = Column(Enum(FriendshipStatusEnum), nullable=False, unique=True)