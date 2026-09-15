from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import relationship

from app.enums import NotificationType
from .base import Base


class Notification(Base):
    __tablename__ = "notification"

    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=True)
    type = Column(Enum(NotificationType), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    recipient = relationship("User", foreign_keys=[recipient_id], back_populates="notifications_received")
    actor = relationship("User", foreign_keys=[actor_id], back_populates="notifications_acted")

    __table_args__ = (
        Index("ix_notification_recipient_id", "recipient_id"),
        Index("ix_notification_created_at", "created_at"),
    )