from typing import Optional
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.enums import PrivacyType
from app.schema.city import CityOut , CityData, CityCreate

class TripBaseOut(OurBaseOut):
    id: int
    title: str
    city: Optional[CityData] = None

class TripCreate(OurBaseModel):
    title: str
    include_home_city: bool = False
    privacy: Optional[PrivacyType] | None

class TripOut(OurBaseModel):
    id: int
    title: str
    city: Optional[CityData] = None

class TripsOut(OurBaseOut):
    trips : list[TripOut] = []