from sqlalchemy import Column, Integer, String
from .base import Base


class City(Base):
    __tablename__ = "city"

    id = Column(Integer, primary_key=True)
    lat = Column(String, nullable=False)
    long = Column(String, nullable=False)