from typing import Optional, List
from datetime import datetime
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.enums import PrivacyType
from app.schema.city import CityOut , CityData, CityCreate
from app.schema.stop import StopInput

from typing import Optional, List
from datetime import datetime
from pydantic import model_validator
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.enums import PrivacyType
from app.schema.city import CityOut, CityData, CityCreate, CityInput
from app.schema.stop import StopInput

class TripCreate(OurBaseModel):
    title:             str
    include_home_city: bool = False
    privacy:           Optional[PrivacyType] = None
    from_city:         Optional[CityInput] = None
    to_city:           Optional[CityInput] = None
    stops:             List[StopInput] = []

    @model_validator(mode="after")
    def check_route_input(self):
        has_from_to = self.from_city is not None or self.to_city is not None
        has_stops = len(self.stops) > 0

        if has_from_to and has_stops:
            raise ValueError("Provide either from_city/to_city or stops, not both.")
        if not has_from_to and not has_stops:
            raise ValueError("You must provide either from_city and to_city, or a list of stops.")
        if (self.from_city is None) != (self.to_city is None):
            raise ValueError("Both from_city and to_city must be provided together.")
        return self
    
    
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
