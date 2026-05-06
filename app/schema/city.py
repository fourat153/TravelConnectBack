from typing import Optional
from app.schema.our_base_model import OurBaseModel, OurBaseOut

class CityOut(OurBaseOut):
    lat : Optional[float] = None
    long : Optional[float] = None

class CityCreate(OurBaseModel):
    lat : Optional[float] = None
    long : Optional[float] = None
class CityData(OurBaseModel):
    id: int
    lat : Optional[float] = None
    long : Optional[float] = None