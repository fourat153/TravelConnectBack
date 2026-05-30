from typing import Optional, List
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.schema.city import CityData

class StopCreate(OurBaseModel):
    lat: float
    long: float
    title: str
    description: Optional[str] = None

class StopOut(OurBaseModel):
    id: int
    trip_id: int
    title: str
    description: Optional[str] = None
    order: int
    city: CityData

class StopBaseOut(OurBaseOut):
    id: Optional[int] = None
    trip_id: Optional[int] = None
    title: Optional[str] = None
    city: Optional[CityData] = None
    order: Optional[int] = None

class StopsOut(OurBaseOut):
    stops: Optional[List[StopOut]] = None

class StopInput(OurBaseModel):
    label: str
    lat:   float
    lon:   float
    order: int
 
