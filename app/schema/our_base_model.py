from typing import Optional

from pydantic import BaseModel

class OurBaseModel(BaseModel):
    class Config:
        from_attributes = True

class OurBaseOut(OurBaseModel):
    message: Optional[str] = None
    status_code: Optional[int] = None