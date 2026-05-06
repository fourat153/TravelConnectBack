from sqlalchemy import Column, Integer, String , Float
from .base import Base


class City(Base):
    __tablename__ = "city"

    id = Column(Integer, primary_key=True)
    lat = Column(Float, nullable=False)
    long = Column(Float, nullable=False)