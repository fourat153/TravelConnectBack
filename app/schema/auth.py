from typing import Optional
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from datetime import datetime

class TokenData(OurBaseModel):
    user_id: int
    expiration: Optional[datetime] = None
class Token(OurBaseOut):
    access_token: Optional[str] = None
    token_type: Optional[str] = None