from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, aliased
from sqlalchemy import or_
from starlette import status
from math import ceil
from ..database import get_db
from app.utils import oauth2
from app import models
from app.schema.friendships import FriendsData, FriendsOut
from app.services.suggestions import get_friend_suggestions
from app.schema.suggestions import SuggestionsOut, SuggestionUser
from app.schema.map_search import MapSearchFriend, MapSearchOut

router = APIRouter()


@router.get("/Friends/search", response_model=MapSearchOut, status_code=status.HTTP_200_OK)
def search_friends(
    q: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    query = (q or "").strip()
    if not query:
        return MapSearchOut(friends=[], stops=[])

    friend_user = aliased(models.User)
    friendship = models.Friendship
    friend_filter = or_(
        (friendship.user_1_id == current_user.user_id) & (friendship.user_2_id == friend_user.id),
        (friendship.user_2_id == current_user.user_id) & (friendship.user_1_id == friend_user.id),
    )
    matching_friends = db.query(friend_user).join(friendship, friend_filter).filter(
        or_(
            friend_user.firstname.ilike(f"%{query}%"),
            friend_user.lastname.ilike(f"%{query}%"),
        )
    ).distinct().all()

    friends = [
        MapSearchFriend(
            friend_id=user.id,
            username=f"{user.firstname} {user.lastname}",
            profile_picture=user.profile_picture,
        )
        for user in matching_friends
    ]
    return MapSearchOut(friends=friends, stops=[])


@router.get("/Friends/me", response_model=FriendsOut, status_code=status.HTTP_200_OK)
def get_my_friends(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
    page_number: int = 1,
    page_size: int = 10,
):
    offset = (page_number - 1) * page_size

    try:
        query = db.query(models.User).join(
            models.Friendship,
            (
                (models.Friendship.user_1_id == current_user.user_id) & (models.Friendship.user_2_id == models.User.id)
            ) | (
                (models.Friendship.user_2_id == current_user.user_id) & (models.Friendship.user_1_id == models.User.id)
            )
        )

        total_records   = query.count()
        total_pages = ceil(total_records / page_size)
        results = query.limit(page_size).offset((page_number - 1) * page_size).all()

        if not results:
            return FriendsOut(
                status_code=status.HTTP_404_NOT_FOUND,
                message="No friends found.",
            )

        friends = [
            FriendsData(
                friend_id       = user.id,
                username        = user.firstname  + " " + user.lastname ,
                profile_picture = user.profile_picture,
            )
            for user in results
        ]

    except Exception as e:
        return FriendsOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
        )

    return FriendsOut(
        status_code = status.HTTP_200_OK,
        message     = "Friends retrieved successfully.",
        data        = friends,
        total_pages = total_pages,
        total_records = total_records,
        page_size   = page_size,
        page_number  = page_number
    )

@router.get("/users/suggestions", response_model=SuggestionsOut, status_code=status.HTTP_200_OK)
def friend_suggestions(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        rows = get_friend_suggestions(current_user.user_id, db)
        data = [
            SuggestionUser(
                id=r.id,
                firstname=r.firstname,
                lastname=r.lastname,
                profile_picture=r.profile_picture,
                mutual_friends_count=r.mutual_friends_count or 0
            )
            for r in rows
        ]
    except Exception as e:
        return SuggestionsOut(status_code=status.HTTP_400_BAD_REQUEST, message=str(e))

    return SuggestionsOut(
        status_code=status.HTTP_200_OK,
        message="Suggestions retrieved successfully",
        data=data
    )

@router.delete("/Friends/me", response_model=FriendsOut, status_code=status.HTTP_200_OK)
def delet () : 
    pass 