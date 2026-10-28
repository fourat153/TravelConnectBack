from datetime import datetime
from .base import Base
from app.enums import FriendshipStatusEnum
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey ,UniqueConstraint, CheckConstraint , Enum
from sqlalchemy.orm import relationship


class FriendshipRequest(Base):
    __tablename__ = "friendship_request"
 
    id          = Column(Integer, primary_key=True)
    sender_id   = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    status_id = Column(Integer, ForeignKey("friendship_status.id"), nullable=False)
    created_at  = Column(DateTime, nullable=False, default=datetime.utcnow)
 
    sender   = relationship("User", foreign_keys=[sender_id],   back_populates="sent_requests")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_requests")
    status   = relationship("FriendshipStatus")
 
    __table_args__ = (
        UniqueConstraint("sender_id", "receiver_id", name="uq_friendship_request_pair"),
        CheckConstraint("sender_id != receiver_id",  name="chk_fr_no_self_request"),
    )
