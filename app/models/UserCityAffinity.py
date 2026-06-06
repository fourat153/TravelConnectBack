from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from Dbengin import Base

class UserCityAffinity(Base):
    __tablename__ = "user_city_affinity"

    id          = Column(Integer, primary_key=True)
    user_id     = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    city_id     = Column(Integer, ForeignKey("city.id", ondelete="CASCADE"), nullable=False)
    visit_count = Column(Integer, nullable=False, default=1)
    updated_at  = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "city_id", name="uq_user_city_affinity"),
    )