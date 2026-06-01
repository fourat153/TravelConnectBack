from typing import Optional, List
from datetime import datetime
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.enums import PrivacyType
from app.schema.city import CityOut , CityData, CityCreate
from app.schema.stop import StopInput

class TripCreate(OurBaseModel):
    title:             str
    include_home_city: bool = False
    privacy:           Optional[PrivacyType] | None
    stops:             List[StopInput] = []
 
 
class TripBaseOut(OurBaseOut):
    id:    int
    title: str
    city:  Optional[CityData] = None
    created_at: Optional[datetime] = None
 
 
class TripOut(OurBaseModel):
    id:    int
    title: str
    city:  Optional[CityData] = None
    created_at: Optional[datetime] = None
 
 
class TripsOut(OurBaseOut):
    trips: list[TripOut] = []
