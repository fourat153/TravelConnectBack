from typing import Literal, Optional

from pydantic import Field

from app.schema.our_base_model import OurBaseModel


class UserSearchResult(OurBaseModel):
    id: int
    name: str
    avatar_url: Optional[str] = Field(default=None, alias="avatarUrl")
    relationship_status: Literal[
        "none", "pending_sent", "pending_received"
    ] = Field(alias="relationshipStatus")
