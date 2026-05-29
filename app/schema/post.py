from typing import Optional
from app.schema.our_base_model import OurBaseModel, OurBaseOut
from datetime import datetime

class ImageOut(OurBaseModel):
    id: int
    link: str
    caption: str | None


class PostOut(OurBaseOut):
    id: int
    stop_id: int
    title: str
    created_at: datetime
    images: list[ImageOut] = []

class PostsOut(OurBaseOut):
    posts: list[PostOut] = []

class SinglePostOut(OurBaseModel):
    post: PostOut | None = None

class FeedPostOut(OurBaseModel):
    id: int
    authorName: str
    authorAvatar: str
    location: str
    imageUrls: list[str] = []
    description: str
    likesCount: int = 0
    hasLiked: bool = False
    comments: list[dict] = []
    createdAt: str
