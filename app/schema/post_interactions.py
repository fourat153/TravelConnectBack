from datetime import datetime
from typing import Optional

from app.schema.our_base_model import OurBaseModel, OurBaseOut


class CommentCreate(OurBaseModel):
    content: str
    parent_id: Optional[int] = None


class CommentData(OurBaseModel):
    id: int
    post_id: int
    user_id: int
    parent_id: Optional[int] = None
    content: str
    created_at: datetime
    username: Optional[str] = "Traveler"


class CommentsOut(OurBaseOut):
    data: list[CommentData] = []


class SingleCommentOut(OurBaseOut):
    data: CommentData | None = None


class LikeData(OurBaseModel):
    id: int
    post_id: int
    user_id: int
    created_at: datetime


class SingleLikeOut(OurBaseOut):
    data: LikeData | None = None
