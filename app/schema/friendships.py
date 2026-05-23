from app.schema.our_base_model import OurBaseModel, OurBaseOut

class FriendsData(OurBaseModel):
    friend_id: int
    username: str

class FriendsOut(OurBaseOut):
    data: list[FriendsData]
    total_pages : int
    total_records : int
    page_size   : int
    page_number  : int 