import logging
from datetime import datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Query, Session, joinedload, selectinload

from app.enums import NotificationType, PrivacyEntityType, PrivacyType
from app.models import (
    City,
    Comment,
    Image,
    Post,
    PostLike,
    PrivacySettings,
    Stop,
    Trip,
    User,
    Video,
)
from app.schema.post import (
    FeedPostOut,
    FeedPostsOut,
    PostOut,
    PostsOut,
)
from app.schema.post_interactions import CommentCreate, CommentData, CommentsOut
from app.services.notification import NotificationError
from app.services.notification_service import create_and_send_notification
from app.services.trip_privacy import (
    can_create_post_on_stop,
    can_delete_post,
    can_view_trip,
    load_trip_visibility_data,
)
from app.utils.cloudinary import upload_image, upload_video
from app.utils.error_handling import exception_handler
from app.utils.pagination import div_ceil

logger = logging.getLogger(__name__)


async def create_post(
    db: Session,
    stop_id: int,
    title: str,
    images: list[UploadFile],
    videos: list[UploadFile],
    user_id: int,
) -> Post:
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Stop not found",
            )
        if not can_create_post_on_stop(stop, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the trip owner can create posts",
            )

        post = Post(stop_id=stop_id, title=title, user_id=user_id)
        db.add(post)
        db.flush()

        for file in images:
            if not file.filename:
                continue
            url = upload_image(await file.read())
            db.add(Image(post_id=post.id, link=url))

        for file in videos:
            if not file.filename:
                continue
            url = upload_video(await file.read())
            db.add(Video(post_id=post.id, link=url))

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

    return post


def delete_post(db: Session, post_id: int, user_id: int) -> None:
    try:
        with db.begin():
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Post not found",
                )
            if not can_delete_post(post, user_id):
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


def create_post_comment(
    db: Session,
    post_id: int,
    payload: CommentCreate,
    user_id: int,
) -> Comment:
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        if not post.stop or not can_view_trip(db, post.stop.trip, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this trip",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

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
            user_id=user_id,
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

            if recipient and recipient.id != user_id:
                commenter_name = f"{user.firstname} {user.lastname}"
                result = create_and_send_notification(
                    db=db,
                    recipient_id=recipient.id,
                    actor_id=user_id,
                    post_id=post_id,
                    notification_type=notification_type,
                    title=notification_title,
                    body=notification_body.format(commenter_name=commenter_name),
                )
                logger.info(
                    "Notification created: id=%s, recipient=%s, actor=%s",
                    result["notification"].id,
                    recipient.id,
                    user_id,
                )
        except NotificationError as e:
            logger.error("Failed to send comment notification (FCM error): %s", e.detail)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "Failed to send comment notification: %s",
                e,
                exc_info=True,
            )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create comment",
        )

    return comment


def like_post(db: Session, post_id: int, user_id: int) -> PostLike:
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found",
            )
        if not post.stop or not can_view_trip(db, post.stop.trip, user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this trip",
            )

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        existing_like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id,
        ).first()
        if existing_like:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already liked this post",
            )

        like = PostLike(post_id=post_id, user_id=user_id)
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

    return like


def unlike_post(db: Session, post_id: int, user_id: int) -> None:
    try:
        like = db.query(PostLike).filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id,
        ).first()

        if not like:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Like not found",
            )
        if not like.post or not like.post.stop or not can_view_trip(
            db,
            like.post.stop.trip,
            user_id,
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


async def create_feed_post(
    db: Session,
    title: str,
    location: str,
    lat: float,
    long: float,
    images: list[UploadFile],
    videos: list[UploadFile],
    user_id: int,
) -> Post:
    try:
        trip = (
            db.query(Trip)
            .filter(Trip.user_id == user_id)
            .order_by(Trip.created_at.desc())
            .first()
        )
        if not trip:
            trip = Trip(user_id=user_id, title="My Travels")
            db.add(trip)
            db.flush()

            trip_privacy = PrivacySettings(
                entity_type=PrivacyEntityType.trip,
                entity_id=trip.id,
                privacy_type=PrivacyType.public,
            )
            db.add(trip_privacy)
            db.flush()

        city = db.query(City).filter(
            City.lat == lat,
            City.long == long,
        ).first()
        if not city:
            city = City(lat=lat, long=long)
            db.add(city)
            db.flush()

        last_stop = (
            db.query(Stop)
            .filter(Stop.trip_id == trip.id)
            .order_by(Stop.order.desc())
            .first()
        )
        order = last_stop.order + 1 if last_stop else 1

        stop = Stop(
            trip_id=trip.id,
            city_id=city.id,
            title=location,
            description=None,
            order=order,
        )
        db.add(stop)
        db.flush()

        post = Post(stop_id=stop.id, title=title, user_id=user_id)
        db.add(post)
        db.flush()

        for file in images:
            if not file.filename:
                continue
            url = upload_image(await file.read())
            db.add(Image(post_id=post.id, link=url))

        for file in videos:
            if not file.filename:
                continue
            url = upload_video(await file.read())
            db.add(Video(post_id=post.id, link=url))

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

    return post


def get_relative_time(value: datetime) -> str:
    diff = datetime.utcnow() - value
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


def get_stop_posts(
    db: Session,
    stop_id: int,
    page_number: int,
    page_size: int,
    viewer_id: int,
) -> PostsOut:
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stop not found",
        )
    if not can_view_trip(db, stop.trip, viewer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    posts_query = (
        db.query(Post)
        .options(
            selectinload(Post.images),
            selectinload(Post.videos),
            selectinload(Post.likes),
        )
        .filter(Post.stop_id == stop_id)
    )
    total_records = posts_query.count()
    posts = posts_query.offset((page_number - 1) * page_size).limit(page_size).all()
    for post in posts:
        post.likes_count = len(post.likes)
        post.has_liked = any(like.user_id == viewer_id for like in post.likes)

    return PostsOut(
        status_code=status.HTTP_200_OK,
        message="Posts retrieved successfully",
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
        posts=[PostOut.model_validate(post) for post in posts],
    )


def get_post_comments(
    db: Session,
    post_id: int,
    page_number: int,
    page_size: int,
    viewer_id: int,
) -> CommentsOut:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )
    if not post.stop or not can_view_trip(db, post.stop.trip, viewer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    comments_query = (
        db.query(Comment)
        .options(joinedload(Comment.user))
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc())
    )
    total_records = comments_query.count()
    comments = comments_query.offset(
        (page_number - 1) * page_size
    ).limit(page_size).all()
    for comment in comments:
        comment.username = (
            f"{comment.user.firstname} {comment.user.lastname}"
            if comment.user
            else "Traveler"
        )

    return CommentsOut(
        status_code=status.HTTP_200_OK,
        message="Comments retrieved successfully",
        data=[CommentData.model_validate(comment) for comment in comments],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )


def _to_feed_post(post: Post, viewer_id: int) -> FeedPostOut:
    stop = post.stop
    trip = stop.trip if stop else None
    user = trip.user if trip else None
    if not stop or not trip or not user:
        raise ValueError(f"Post {post.id} is missing its trip or author")

    comments = [
        {
            "id": comment.id,
            "userId": comment.user_id,
            "username": (
                f"{comment.user.firstname} {comment.user.lastname}"
                if comment.user
                else "Traveler"
            ),
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
        authorAvatar=user.profile_picture,
        tripTitle=trip.title,
        location=stop.title,
        imageUrls=[image.link for image in post.images],
        videoUrls=[video.link for video in post.videos],
        description=post.title,
        likesCount=len(post.likes),
        hasLiked=any(like.user_id == viewer_id for like in post.likes),
        comments=comments,
        createdAt=get_relative_time(post.created_at),
        lat=stop.city.lat if stop.city else None,
        long=stop.city.long if stop.city else None,
    )


def _load_feed_posts(query: Query[Post]) -> list[Post]:
    return (
        query.options(
            joinedload(Post.stop).joinedload(Stop.trip).joinedload(Trip.user),
            joinedload(Post.stop).joinedload(Stop.city),
            selectinload(Post.images),
            selectinload(Post.videos),
            selectinload(Post.likes),
            selectinload(Post.comments).joinedload(Comment.user),
        )
        .all()
    )


def _visible_feed_posts(
    db: Session,
    posts: list[Post],
    viewer_id: int,
) -> list[Post]:
    trips_by_id = {
        post.stop.trip.id: post.stop.trip
        for post in posts
        if post.stop and post.stop.trip
    }
    privacy_by_trip, friend_ids = load_trip_visibility_data(
        db,
        list(trips_by_id.values()),
        viewer_id,
    )
    return [
        post
        for post in posts
        if post.stop
        and post.stop.trip
        and post.stop.trip.user
        and can_view_trip(
            db,
            post.stop.trip,
            viewer_id,
            friend_ids=friend_ids,
            privacy_by_trip=privacy_by_trip,
        )
    ]


def get_feed_posts(
    db: Session,
    page_number: int,
    page_size: int,
    viewer_id: int,
) -> FeedPostsOut:
    posts = _load_feed_posts(
        db.query(Post).join(Stop).join(Trip).order_by(Post.created_at.desc()),
    )
    feed_posts = [
        _to_feed_post(post, viewer_id)
        for post in _visible_feed_posts(db, posts, viewer_id)
    ]

    total_records = len(feed_posts)
    page_start = (page_number - 1) * page_size
    return FeedPostsOut(
        posts=feed_posts[page_start:page_start + page_size],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )


def get_post_by_id(db: Session, post_id: int, viewer_id: int) -> FeedPostOut:
    posts = _load_feed_posts(
        db.query(Post).filter(Post.id == post_id),
    )
    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    post = posts[0]
    if not post.stop or not post.stop.trip or not post.stop.trip.user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post details not found",
        )
    if not can_view_trip(db, post.stop.trip, viewer_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    return _to_feed_post(post, viewer_id)


def get_user_posts(
    db: Session,
    user_id: int,
    page_number: int,
    page_size: int,
    viewer_id: int,
) -> FeedPostsOut:
    posts = _load_feed_posts(
        db.query(Post)
        .join(Stop)
        .join(Trip)
        .filter(Trip.user_id == user_id)
        .order_by(Post.created_at.desc()),
    )
    user_posts = [
        _to_feed_post(post, viewer_id)
        for post in _visible_feed_posts(db, posts, viewer_id)
    ]

    total_records = len(user_posts)
    page_start = (page_number - 1) * page_size
    return FeedPostsOut(
        posts=user_posts[page_start:page_start + page_size],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )
