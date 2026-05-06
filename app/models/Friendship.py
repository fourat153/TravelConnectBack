from datetime import datetime
from .base import Base
from sqlalchemy import Column, DateTime, Integer, String, ForeignKey,UniqueConstraint, CheckConstraint
from sqlalchemy.orm import relationship

class Friendship(Base):
    __tablename__ = "friendship"
 
    id         = Column(Integer, primary_key=True)
    user_1_id  = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    user_2_id  = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
 
    user_1 = relationship("User", foreign_keys=[user_1_id], back_populates="friendships_as_user1")
    user_2 = relationship("User", foreign_keys=[user_2_id], back_populates="friendships_as_user2")
 
    __table_args__ = (
        UniqueConstraint("user_1_id", "user_2_id", name="uq_friendship_pair"),
        CheckConstraint("user_1_id != user_2_id",   name="chk_f_no_self_friendship"),
    )
 
