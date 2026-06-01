from datetime import datetime
from typing import Annotated, List

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from Dbengin import get_db
from app.enums.privacy_entity_type import PrivacyEntityType
from app.enums.privacy_type import PrivacyType
from app.models.Friendship import Friendship
from app.models.city import City
from app.models.comment import Comment
from app.models.image import Image
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.privacy_setting import PrivacySettings
from app.models.stop import Stop
from app.models.trip import Trip
from app.models.user import User
from app.schema.post_interactions import CommentCreate, CommentData, CommentsOut, LikeData, SingleCommentOut, SingleLikeOut
from app.schema.post import FeedPostOut, PostOut, PostsOut, SinglePostOut
from app.utils import oauth2
from app.utils.cloudinary import upload_image
from app.utils.error_handling import exception_handler

router = APIRouter()


def get_relative_time(dt: datetime) -> str:
    diff = datetime.utcnow() - dt
    seconds = diff.total_seconds()
    if seconds < 60:
        return "Just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{int(hours)}h ago"
    days = hours // 24
    if days < 30:
        return f"{int(days)}d ago"
    months = days // 30
    if months < 12:
        return f"{int(months)}mo ago"
    years = months // 12
    return f"{int(years)}y ago"


@router.get('/stops/{stop_id}/posts', response_model=PostsOut, status_code=status.HTTP_200_OK)
def get_stop_posts(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        return PostsOut(status_code=status.HTTP_404_NOT_FOUND, message="Stop not found")

    posts = db.query(Post).filter(Post.stop_id == stop_id).all()
    for p in posts:
        p.likes_count = len(p.likes)
        p.has_liked = any(like.user_id == current_user.user_id for like in p.likes)

    return PostsOut(
        status_code=status.HTTP_200_OK,
        message="Posts retrieved successfully",
        posts=[PostOut.model_validate(p) for p in posts]
    )


@router.post('/stops/{stop_id}/posts', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    stop_id: int,
    title: Annotated[str, Form()],
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            return SinglePostOut(status_code=status.HTTP_404_NOT_FOUND, message="Stop not found")

        post = Post(stop_id=stop_id, title=title)
        db.add(post)
        db.flush()

        for file in images:
            if not file.filename:
                continue
            url = upload_image(file.file.read())
            img = Image(post_id=post.id, link=url)
            db.add(img)

        db.commit()
        db.refresh(post)

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SinglePostOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SinglePostOut(
        status_code=status.HTTP_201_CREATED,
        message="Post created successfully",
        post=PostOut.model_validate(post)
    )


@router.delete('/posts/{post_id}', response_model=SinglePostOut, status_code=status.HTTP_200_OK)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return SinglePostOut(status_code=status.HTTP_404_NOT_FOUND, message="Post not found")

        db.delete(post)
        db.commit()

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SinglePostOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SinglePostOut(
        status_code=status.HTTP_200_OK,
        message="Post deleted successfully",
    )


@router.get('/posts/{post_id}/comments', response_model=CommentsOut, status_code=status.HTTP_200_OK)
def get_post_comments(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        return CommentsOut(status_code=status.HTTP_404_NOT_FOUND, message="Post not found")

    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.desc()).all()
    for comment in comments:
        comment.username = f"{comment.user.firstname} {comment.user.lastname}" if comment.user else "Traveler"

    return CommentsOut(
        status_code=status.HTTP_200_OK,
        message="Comments retrieved successfully",
        data=[CommentData.model_validate(comment) for comment in comments]
    )


@router.post('/posts/{post_id}/comments', response_model=SingleCommentOut, status_code=status.HTTP_201_CREATED)
def create_post_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return SingleCommentOut(status_code=status.HTTP_404_NOT_FOUND, message="Post not found")

        user = db.query(User).filter(User.id == current_user.user_id).first()
        if not user:
            return SingleCommentOut(status_code=status.HTTP_404_NOT_FOUND, message="User not found")

        comment = Comment(post_id=post_id, user_id=current_user.user_id, content=payload.content)
        db.add(comment)
        db.commit()
        db.refresh(comment)
        comment.username = f"{user.firstname} {user.lastname}"

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SingleCommentOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SingleCommentOut(
        status_code=status.HTTP_201_CREATED,
        message="Comment created successfully",
        data=CommentData.model_validate(comment)
    )


@router.post('/posts/{post_id}/likes', response_model=SingleLikeOut, status_code=status.HTTP_201_CREATED)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return SingleLikeOut(status_code=status.HTTP_404_NOT_FOUND, message="Post not found")

        user = db.query(User).filter(User.id == current_user.user_id).first()
        if not user:
            return SingleLikeOut(status_code=status.HTTP_404_NOT_FOUND, message="User not found")

        existing_like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.user_id
        ).first()
        if existing_like:
            return SingleLikeOut(
                status_code=status.HTTP_409_CONFLICT,
                message="You already liked this post",
                data=LikeData.model_validate(existing_like)
            )

        like = PostLike(post_id=post_id, user_id=current_user.user_id)
        db.add(like)
        db.commit()
        db.refresh(like)

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SingleLikeOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SingleLikeOut(
        status_code=status.HTTP_201_CREATED,
        message="Post liked successfully",
        data=LikeData.model_validate(like)
    )


@router.delete('/posts/{post_id}/likes', response_model=SingleLikeOut, status_code=status.HTTP_200_OK)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.user_id
        ).first()

        if not like:
            return SingleLikeOut(status_code=status.HTTP_404_NOT_FOUND, message="Like not found")

        db.delete(like)
        db.commit()

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SingleLikeOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SingleLikeOut(
        status_code=status.HTTP_200_OK,
        message="Post unliked successfully",
    )


@router.get('/posts/feed', response_model=List[FeedPostOut], status_code=status.HTTP_200_OK)
def get_feed_posts(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    posts = db.query(Post).join(Stop).join(Trip).order_by(Post.created_at.desc()).all()

    feed_posts = []
    for post in posts:
        stop = post.stop
        trip = stop.trip if stop else None
        user = trip.user if trip else None

        if not stop or not trip or not user:
            continue

        author_name = f"{user.firstname} {user.lastname}"
        author_avatar = user.profile_picture if user.profile_picture else "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80"
        image_urls = [img.link for img in post.images]
        likes_count = len(post.likes)
        has_liked = any(like.user_id == current_user.user_id for like in post.likes)
        comments = [
            {
                "id": comment.id,
                "userId": comment.user_id,
                "username": f"{comment.user.firstname} {comment.user.lastname}" if comment.user else "Traveler",
                "text": comment.content,
                "createdAt": get_relative_time(comment.created_at),
            }
            for comment in post.comments
        ]

        feed_posts.append(FeedPostOut(
            id=post.id,
            authorName=author_name,
            authorAvatar=author_avatar,
            location=stop.title,
            imageUrls=image_urls,
            description=post.title,
            likesCount=likes_count,
            hasLiked=has_liked,
            comments=comments,
            createdAt=get_relative_time(post.created_at)
        ))

    return feed_posts


@router.post('/posts/feed', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
def create_feed_post(
    title: Annotated[str, Form()],
    location: Annotated[str, Form()],
    lat: Annotated[float, Form()] = 0.0,
    long: Annotated[float, Form()] = 0.0,
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        trip = db.query(Trip).filter(Trip.user_id == current_user.user_id).order_by(Trip.created_at.desc()).first()
        if not trip:
            trip = Trip(user_id=current_user.user_id, title="My Travels")
            db.add(trip)
            db.flush()

            trip_privacy = PrivacySettings(
                entity_type=PrivacyEntityType.trip,
                entity_id=trip.id,
                privacy_type=PrivacyType.public
            )
            db.add(trip_privacy)
            db.flush()

        city = db.query(City).filter(City.lat == lat, City.long == long).first()
        if not city:
            city = City(lat=lat, long=long)
            db.add(city)
            db.flush()

        last_stop = db.query(Stop).filter(Stop.trip_id == trip.id).order_by(Stop.order.desc()).first()
        order = (last_stop.order + 1) if last_stop else 1

        stop = Stop(
            trip_id=trip.id,
            city_id=city.id,
            title=location,
            description=None,
            order=order
        )
        db.add(stop)
        db.flush()

        post = Post(stop_id=stop.id, title=title)
        db.add(post)
        db.flush()

        for file in images:
            if not file.filename:
                continue
            url = upload_image(file.file.read())
            img = Image(post_id=post.id, link=url)
            db.add(img)

        db.commit()
        db.refresh(post)

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SinglePostOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SinglePostOut(
        status_code=status.HTTP_201_CREATED,
        message="Feed post created successfully",
        post=PostOut.model_validate(post)
    )
