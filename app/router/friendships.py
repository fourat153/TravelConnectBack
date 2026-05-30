from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status
from math import ceil
from ..database import get_db
from app.utils import oauth2
from app import models
from app.schema.friendships import FriendsData, FriendsOut

router = APIRouter()


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

@router.delete("/Friends/me", response_model=FriendsOut, status_code=status.HTTP_200_OK)
def delet () : 
    pass 