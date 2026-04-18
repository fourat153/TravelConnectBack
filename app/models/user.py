from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from Dbengin import Base
from app.enums import GenderEnum, AccountStatusEnum , ConfirmedEnum
from sqlalchemy import Boolean

class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String(50), nullable=False, unique=True)
    password = Column(String, nullable=False)
    firstname = Column(String(50), nullable=False)
    lastname = Column(String(50), nullable=False)
    gender = Column(Enum(GenderEnum), nullable=True)
    phone_number = Column(String(20), nullable=True)
    status = Column(Enum(AccountStatusEnum), nullable=False, default=AccountStatusEnum.inactive)
    is_confirmed = Column(Enum(ConfirmedEnum), nullable=False, default=ConfirmedEnum.NotConfirmed)
    city_id = Column(Integer, ForeignKey("city.id"), nullable=True)
    privacy_id = Column(Integer, ForeignKey("privacy.id"), nullable=True)

    city = relationship("City")
    privacy = relationship("Privacy")