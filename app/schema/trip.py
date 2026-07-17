from typing import Optional, List
from datetime import datetime
from pydantic import model_validator
from app.enums import PrivacyType
from app.schema.city import CityInput, CityData
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.schema.stop import StopInput

class TripCreate(OurBaseModel):
    title:             str
    privacy:           Optional[PrivacyType] = None
    from_city:         CityInput
    to_city:           CityInput
    @model_validator(mode="after")
    def validate_route(self):
            if (
            self.from_city.lat == self.to_city.lat
            and self.from_city.lon == self.to_city.lon
            ):
                raise ValueError("Departure and destination cannot be the same location.")
            return self

class TripBaseOut(OurBaseOut):
    id:    int
    title: str
    created_at: Optional[datetime] = None
 
 
class TripsOut(OurBaseOut):
    trips: list[TripBaseOut] = []
