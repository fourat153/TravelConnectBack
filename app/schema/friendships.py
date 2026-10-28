from typing import Optional
from app.schema.our_base_model import OurBaseModel, PaginatedResponse

class FriendsData(OurBaseModel):
    friend_id: int
    username: str
    profile_picture: Optional[str] = None

class FriendsOut(PaginatedResponse):
    data: list[FriendsData]
    total_pages : int
    total_records : int
    page_size   : int
    page_number  : int 

class FriendFirstStop(OurBaseModel):
    lat: float
    lon: float
    stop_title: str
 