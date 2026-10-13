import logging
from datetime import datetime
from typing import Annotated, List
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload, selectinload
from Dbengin import get_db
from app.enums.privacy_entity_type import PrivacyEntityType
from app.enums.privacy_type import PrivacyType
from app.enums import NotificationType
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
from app.models.video import Video
from app.schema.post_interactions import CommentCreate, CommentData, CommentsOut, LikeData, SingleCommentOut, SingleLikeOut
from app.schema.post import FeedPostOut, PostOut, PostsOut, SinglePostOut
from app.services.notification_service import create_and_send_notification
from app.services.notification import NotificationError
from app.utils import oauth2
from app.utils.cloudinary import upload_image, upload_video
from app.utils.error_handling import exception_handler
from app.services.trip_privacy import can_view_trip

router = APIRouter()
logger = logging.getLogger(__name__)

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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")
    if not can_view_trip(db, stop.trip, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    posts = (
        db.query(Post)
        .options(
            selectinload(Post.images),
            selectinload(Post.videos),
            selectinload(Post.likes),
        )
        .filter(Post.stop_id == stop_id)
        .all()
    )
    for p in posts:
        p.likes_count = len(p.likes)
        p.has_liked = any(like.user_id == current_user.user_id for like in p.likes)

    return PostsOut(
        status_code=status.HTTP_200_OK,
        message="Posts retrieved successfully",
        posts=[PostOut.model_validate(p) for p in posts]
    )

@router.post('/stops/{stop_id}/posts', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    stop_id: int,
    title: Annotated[str, Form()],
    images: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")
        if stop.trip.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the trip owner can create posts",
            )

        post = Post(stop_id=stop_id, title=title, user_id=current_user.user_id)
        db.add(post)
        db.flush()

        for file in images:
            if not file.filename:
                continue
            url = upload_image(await file.read())
            img = Image(post_id=post.id, link=url)
            db.add(img)

        for file in videos:
            if not file.filename:
                continue
            url = upload_video(await file.read())
            vid = Video(post_id=post.id, link=url)
            db.add(vid)

        db.commit()
        db.refresh(post)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create post",
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
        with db.begin():
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found",
                )
            if post.user_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the post author can delete this post",
                )

            db.delete(post)

    except HTTPException:
        raise
    except Exception as e:
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete post",
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if not post.stop or not can_view_trip(db, post.stop.trip, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    comments = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc())
        .all()
    )
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        if not post.stop or not can_view_trip(db, post.stop.trip, current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this trip",
            )

        user = db.query(User).filter(User.id == current_user.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        parent_comment = None
        if payload.parent_id is not None:
            parent_comment = db.query(Comment).filter(
                Comment.id == payload.parent_id,
                Comment.post_id == post_id,
            ).first()
            if not parent_comment:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent comment not found",
                )

        comment = Comment(
            post_id=post_id,
            user_id=current_user.user_id,
            parent_id=payload.parent_id,
            content=payload.content,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        comment.username = f"{user.firstname} {user.lastname}"

        try:
            if parent_comment:
                recipient = parent_comment.user
                notification_type = NotificationType.COMMENT_REPLY
                notification_title = "New Reply"
                notification_body = "{commenter_name} replied to your comment"
            else:
                recipient = post.stop.trip.user if post.stop and post.stop.trip else None
                notification_type = NotificationType.POST_COMMENT
                notification_title = "New Comment"
                notification_body = "{commenter_name} commented on your post"

            if recipient and recipient.id != current_user.user_id:
                commenter_name = f"{user.firstname} {user.lastname}"
                result = create_and_send_notification(
                    db=db,
                    recipient_id=recipient.id,
                    actor_id=current_user.user_id,
                    post_id=post_id,
                    notification_type=notification_type,
                    title=notification_title,
                    body=notification_body.format(commenter_name=commenter_name),
                )
                logger.info(f"Notification created: id={result['notification'].id}, recipient={recipient.id}, actor={current_user.user_id}")
        except NotificationError as e:
            logger.error(f"Failed to send comment notification (FCM error): {e.detail}")
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send comment notification: {str(e)}", exc_info=True)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment",
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
        if not post.stop or not can_view_trip(db, post.stop.trip, current_user.user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this trip",
            )

        user = db.query(User).filter(User.id == current_user.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        existing_like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == current_user.user_id
        ).first()
        if existing_like:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already liked this post",
            )

        like = PostLike(post_id=post_id, user_id=current_user.user_id)
        db.add(like)
        db.commit()
        db.refresh(like)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to like post",
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Like not found")
        if not like.post or not like.post.stop or not can_view_trip(
            db, like.post.stop.trip, current_user.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this trip",
            )

        db.delete(like)
        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlike post",
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
    posts = (
        db.query(Post)
        .options(
            joinedload(Post.stop).joinedload(Stop.trip).joinedload(Trip.user),
            joinedload(Post.stop).joinedload(Stop.city),
            selectinload(Post.images),
            selectinload(Post.videos),
            selectinload(Post.likes),
            selectinload(Post.comments).joinedload(Comment.user),
        )
        .join(Stop)
        .join(Trip)
        .order_by(Post.created_at.desc())
        .all()
    )

    friend_ids = {
        friendship.user_2_id
        if friendship.user_1_id == current_user.user_id
        else friendship.user_1_id
        for friendship in db.query(Friendship).filter(
            (Friendship.user_1_id == current_user.user_id)
            | (Friendship.user_2_id == current_user.user_id)
        ).all()
    }

    feed_posts = []
    for post in posts:
        stop = post.stop
        trip = stop.trip if stop else None
        user = trip.user if trip else None

        if not stop or not trip or not user or not can_view_trip(
            db, trip, current_user.user_id, friend_ids
        ):
            continue

        author_name = f"{user.firstname} {user.lastname}"
        author_avatar = user.profile_picture
        image_urls = [img.link for img in post.images]
        video_urls = [vid.link for vid in post.videos]
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
            stop_id=stop.id,
            trip_id=trip.id,
            authorId=user.id,
            authorName=author_name,
            authorAvatar=author_avatar,
            location=stop.title,
            tripTitle=trip.title,
            imageUrls=image_urls,
            videoUrls=video_urls,
            description=post.title,
            likesCount=likes_count,
            hasLiked=has_liked,
            comments=comments,
            createdAt=get_relative_time(post.created_at),
            lat=stop.city.lat if stop.city else None,
            long=stop.city.long if stop.city else None
        ))

    return feed_posts

@router.get('/posts/{post_id}', response_model=FeedPostOut, status_code=status.HTTP_200_OK)
def get_post_by_id(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    post = (
        db.query(Post)
        .options(
            joinedload(Post.stop).joinedload(Stop.trip).joinedload(Trip.user),
            joinedload(Post.stop).joinedload(Stop.city),
            selectinload(Post.images),
            selectinload(Post.videos),
            selectinload(Post.likes),
            selectinload(Post.comments).joinedload(Comment.user),
        )
        .filter(Post.id == post_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    stop = post.stop
    trip = stop.trip if stop else None
    user = trip.user if trip else None
    if not stop or not trip or not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post details not found")
    if not can_view_trip(db, trip, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    author_avatar = user.profile_picture
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

    return FeedPostOut(
        id=post.id,
        stop_id=stop.id,
        trip_id=trip.id,
        authorId=user.id,
        authorName=f"{user.firstname} {user.lastname}",
        authorAvatar=author_avatar,
        tripTitle=trip.title,
        location=stop.title,
        imageUrls=[image.link for image in post.images],
        videoUrls=[video.link for video in post.videos],
        description=post.title,
        likesCount=len(post.likes),
        hasLiked=any(like.user_id == current_user.user_id for like in post.likes),
        comments=comments,
        createdAt=get_relative_time(post.created_at),
        lat=stop.city.lat if stop.city else None,
        long=stop.city.long if stop.city else None,
    )

@router.get('/posts/user/{user_id}', response_model=List[FeedPostOut], status_code=status.HTTP_200_OK)
def get_user_posts(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    posts = (
        db.query(Post)
        .options(
            joinedload(Post.stop).joinedload(Stop.trip).joinedload(Trip.user),
            joinedload(Post.stop).joinedload(Stop.city),
            selectinload(Post.images),
            selectinload(Post.videos),
            selectinload(Post.likes),
            selectinload(Post.comments).joinedload(Comment.user),
        )
        .join(Stop)
        .join(Trip)
        .filter(Trip.user_id == user_id)
        .order_by(Post.created_at.desc())
        .all()
    )

    user_posts = []
    for post in posts:
        stop = post.stop
        trip = stop.trip if stop else None
        user = trip.user if trip else None

        if not stop or not trip or not user:
            continue
        if not can_view_trip(db, trip, current_user.user_id):
            continue

        author_name = f"{user.firstname} {user.lastname}"
        author_avatar = user.profile_picture
        image_urls = [img.link for img in post.images]
        video_urls = [vid.link for vid in post.videos]
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

        user_posts.append(FeedPostOut(
            id=post.id,
            stop_id=stop.id,
            trip_id=trip.id,
            authorId=user.id,
            authorName=author_name,
            authorAvatar=author_avatar,
            location=stop.title,
            tripTitle=trip.title,
            imageUrls=image_urls,
            videoUrls=video_urls,
            description=post.title,
            likesCount=likes_count,
            hasLiked=has_liked,
            comments=comments,
            createdAt=get_relative_time(post.created_at),
            lat=stop.city.lat if stop.city else None,
            long=stop.city.long if stop.city else None
        ))

    return user_posts

@router.post('/posts/feed', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
async def create_feed_post(
    title: Annotated[str, Form()],
    location: Annotated[str, Form()],
    lat: Annotated[float, Form()] = 0.0,
    long: Annotated[float, Form()] = 0.0,
    images: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
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

        post = Post(stop_id=stop.id, title=title, user_id=current_user.user_id)
        db.add(post)
        db.flush()

        for file in images:
            if not file.filename:
                continue
            url = upload_image(await file.read())
            img = Image(post_id=post.id, link=url)
            db.add(img)

        for file in videos:
            if not file.filename:
                continue
            url = upload_video(await file.read())
            vid = Video(post_id=post.id, link=url)
            db.add(vid)

        db.commit()
        db.refresh(post)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create feed post",
        )

    return SinglePostOut(
        status_code=status.HTTP_201_CREATED,
        message="Feed post created successfully",
        post=PostOut.model_validate(post)
    )
