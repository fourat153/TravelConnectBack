from typing import Optional
from app.schema.ourBaseModel import OurBaseModel, OurBaseOut
from app.enums import GenderEnum


class UserCreate(OurBaseModel):
    email : str
    password : str
    confirm_password : str
    firstname : str
    lastname : str
    phone_number: Optional[str] = None
    gender: GenderEnum
class UserOut(OurBaseOut):
    id: int | None = None
    email : str | None = None
    firstname : str | None = None
    lastname : str | None = None
    phone_number: Optional[str] = None