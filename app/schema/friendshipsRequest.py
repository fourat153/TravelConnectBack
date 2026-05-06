from app.schema.our_base_model import OurBaseModel, OurBaseOut
from typing import Optional


class FriendshipRequestCreate(OurBaseModel):
    receiver_id: int


class FriendshipRequestOut(OurBaseOut):
    id:          Optional[int] = None
    sender_id:   Optional[int] = None
    receiver_id: Optional[int] = None