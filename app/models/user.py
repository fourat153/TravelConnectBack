from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from Dbengin import Base
from app.enums import GenderEnum, AccountStatusEnum , ConfirmedEnum
from sqlalchemy import Boolean
from app.enums import Onboarding

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
    has_completed_onboarding= Column(Enum(Onboarding) , nullable = False  , default = Onboarding.Not_Onboarded ,  server_default='Not_Onboarded')

    city = relationship("City")
    sent_requests        = relationship("FriendshipRequest", foreign_keys="FriendshipRequest.sender_id",   back_populates="sender")
    received_requests    = relationship("FriendshipRequest", foreign_keys="FriendshipRequest.receiver_id", back_populates="receiver")
    friendships_as_user1 = relationship("Friendship", foreign_keys="Friendship.user_1_id", back_populates="user_1")
    friendships_as_user2 = relationship("Friendship", foreign_keys="Friendship.user_2_id", back_populates="user_2")