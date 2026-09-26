from typing import Optional

from app.schema.our_base_model import OurBaseModel


class MapSearchFriend(OurBaseModel):
    friend_id: int
    username: str
    profile_picture: Optional[str] = None


class MapSearchCity(OurBaseModel):
    name: Optional[str] = None
    lat: float
    long: float


class MapSearchStop(OurBaseModel):
    id: int
    trip_id: int
    title: Optional[str] = None
    city: MapSearchCity


class MapSearchOut(OurBaseModel):
    friends: list[MapSearchFriend]
    stops: list[MapSearchStop]