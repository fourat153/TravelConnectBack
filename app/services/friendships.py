from fastapi import HTTPException, status
from sqlalchemy import case, exists, or_
from sqlalchemy.orm import Session, aliased

from app import models
from app.enums import FriendshipStatusEnum
from app.schema.friendships import FriendsData, FriendsOut
from app.schema.map_search import MapSearchFriend, MapSearchOut
from app.schema.our_base_model import OurBaseOut
from app.schema.pagination import UserSearchOut
from app.schema.user_search import UserSearchResult
from app.utils.pagination import div_ceil


def search_friends(
    db: Session,
    current_user_id: int,
    query: str | None,
    page_number: int,
    page_size: int,
) -> MapSearchOut:
    search_term = (query or "").strip()
    if not search_term:
        return MapSearchOut(
            friends=[],
            stops=[],
            page_number=page_number,
            page_size=page_size,
            total_pages=0,
            total_records=0,
        )

    friend_user = aliased(models.User)
    friendship = models.Friendship
    friend_filter = or_(
        (friendship.user_1_id == current_user_id)
        & (friendship.user_2_id == friend_user.id),
        (friendship.user_2_id == current_user_id)
        & (friendship.user_1_id == friend_user.id),
    )
    friends_query = db.query(friend_user).join(
        friendship,
        friend_filter,
    ).filter(
        or_(
            friend_user.firstname.ilike(f"%{search_term}%"),
            friend_user.lastname.ilike(f"%{search_term}%"),
        )
    ).distinct()
    total_records = friends_query.count()
    matching_friends = friends_query.offset(
        (page_number - 1) * page_size
    ).limit(page_size).all()

    return MapSearchOut(
        friends=[
            MapSearchFriend(
                friend_id=user.id,
                username=f"{user.firstname} {user.lastname}",
                profile_picture=user.profile_picture,
            )
            for user in matching_friends
        ],
        stops=[],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )


def get_my_friends(
    db: Session,
    current_user_id: int,
    page_number: int,
    page_size: int,
) -> FriendsOut:
    try:
        query = db.query(models.User).join(
            models.Friendship,
            (
                (models.Friendship.user_1_id == current_user_id)
                & (models.Friendship.user_2_id == models.User.id)
            )
            | (
                (models.Friendship.user_2_id == current_user_id)
                & (models.Friendship.user_1_id == models.User.id)
            ),
        )

        total_records = query.count()
        total_pages = div_ceil(total_records, page_size)
        results = query.limit(page_size).offset(
            (page_number - 1) * page_size
        ).all()

        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No friends found.",
            )

        friends = [
            FriendsData(
                friend_id=user.id,
                username=f"{user.firstname} {user.lastname}",
                profile_picture=user.profile_picture,
            )
            for user in results
        ]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve friends",
        )

    return FriendsOut(
        status_code=status.HTTP_200_OK,
        message="Friends retrieved successfully.",
        data=friends,
        total_pages=total_pages,
        total_records=total_records,
        page_size=page_size,
        page_number=page_number,
    )


def search_users(
    db: Session,
    current_user_id: int,
    query: str,
    page_number: int,
    page_size: int,
) -> UserSearchOut:
    search_term = query.strip()
    if not search_term:
        return UserSearchOut(
            users=[],
            page_number=page_number,
            page_size=page_size,
            total_pages=0,
            total_records=0,
        )

    user = models.User
    friendship = models.Friendship
    friend_request = models.FriendshipRequest
    friendship_status = models.FriendshipStatus
    pending_request = (
        friend_request.status_id == friendship_status.id
    ) & (friendship_status.name == FriendshipStatusEnum.pending)

    is_pending_sent = exists().where(
        pending_request
        & (friend_request.sender_id == current_user_id)
        & (friend_request.receiver_id == user.id)
    )
    is_pending_received = exists().where(
        pending_request
        & (friend_request.sender_id == user.id)
        & (friend_request.receiver_id == current_user_id)
    )
    is_friend = exists().where(
        or_(
            (friendship.user_1_id == current_user_id)
            & (friendship.user_2_id == user.id),
            (friendship.user_1_id == user.id)
            & (friendship.user_2_id == current_user_id),
        )
    )

    relationship_status = case(
        (is_pending_sent, "pending_sent"),
        (is_pending_received, "pending_received"),
        else_="none",
    ).label("relationship_status")

    rows_query = db.query(
        user.id,
        (user.firstname + " " + user.lastname).label("name"),
        user.profile_picture.label("avatar_url"),
        relationship_status,
    ).filter(
        user.id != current_user_id,
        ~is_friend,
        or_(
            user.email.ilike(f"%{search_term}%"),
            (user.firstname + " " + user.lastname).ilike(
                f"%{search_term}%"
            ),
            (user.firstname + user.lastname).ilike(f"%{search_term}%"),
        ),
    ).order_by(user.firstname, user.lastname, user.id)
    total_records = rows_query.count()
    rows = rows_query.offset((page_number - 1) * page_size).limit(page_size).all()

    return UserSearchOut(
        users=[
            UserSearchResult(
                id=row.id,
                name=row.name,
                avatar_url=row.avatar_url,
                relationship_status=row.relationship_status,
            )
            for row in rows
        ],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )


def delete_friend(
    db: Session,
    current_user_id: int,
    friend_id: int,
) -> OurBaseOut:
    try:
        friendship = db.query(models.Friendship).filter(
            or_(
                (models.Friendship.user_1_id == current_user_id)
                & (models.Friendship.user_2_id == friend_id),
                (models.Friendship.user_1_id == friend_id)
                & (models.Friendship.user_2_id == current_user_id),
            )
        ).first()

        if not friendship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Friendship not found.",
            )

        db.delete(friendship)
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove friend",
        )

    return OurBaseOut(
        status_code=status.HTTP_200_OK,
        message="Friend removed successfully.",
    )
