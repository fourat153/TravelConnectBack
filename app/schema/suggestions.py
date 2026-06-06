
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from typing import Optional, List

class SuggestionUser(OurBaseModel):
    id: int
    firstname: str
    lastname: str
    profile_picture: Optional[str] = None
    mutual_friends_count: int = 0

class SuggestionsOut(OurBaseOut):
    data: List[SuggestionUser] = []