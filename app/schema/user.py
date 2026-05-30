from typing import Optional
from app.schema.city import CityOut
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from app.enums import GenderEnum , AccountStatusEnum , ConfirmedEnum 
from app.enums import Onboarding

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
    gender: Optional[GenderEnum] = None
    profile_picture: Optional[str] = None
    has_completed_onboarding: Onboarding | None = None
class UserConfirm(OurBaseModel):
    is_confirmed: ConfirmedEnum
    status: AccountStatusEnum