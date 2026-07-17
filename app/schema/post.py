from datetime import datetime
from pydantic import Field

from app.schema.our_base_model import OurBaseModel, OurBaseOut


class ImageOut(OurBaseModel):
    id: int
    link: str
    caption: str | None = None


class VideoOut(OurBaseModel):
    id: int
    link: str
    caption: str | None = None


class PostOut(OurBaseOut):
    id: int
    stop_id: int
    title: str
    created_at: datetime
    images: list[ImageOut] = Field(default_factory=list)
    videos: list[VideoOut] = Field(default_factory=list)
    likes_count: int = 0
    has_liked: bool = False


class PostsOut(OurBaseOut):
    posts: list[PostOut] = Field(default_factory=list)


class SinglePostOut(OurBaseModel):
    post: PostOut | None = None


class FeedPostOut(OurBaseModel):
    id: int
    author_id: int = Field(alias="authorId")
    author_name: str = Field(alias="authorName")
    author_avatar: str = Field(alias="authorAvatar")
    trip_title: str | None = Field(default=None, alias="tripTitle")
    location: str
    image_urls: list[str] = Field(default_factory=list, alias="imageUrls")
    video_urls: list[str] = Field(default_factory=list, alias="videoUrls")
    description: str
    likes_count: int = Field(default=0, alias="likesCount")
    has_liked: bool = Field(default=False, alias="hasLiked")
    comments: list[dict] = Field(default_factory=list)
    created_at: str = Field(alias="createdAt")