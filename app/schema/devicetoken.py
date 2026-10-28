from app.schema.our_base_model import OurBaseModel,OurBaseOut


from pydantic import BaseModel


class DeviceTokenCreate(BaseModel):
    token: str

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DeviceTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    token: str
    created_at: datetime
    updated_at: datetime