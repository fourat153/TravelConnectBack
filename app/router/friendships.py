from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from starlette import status
from ..database import get_db
from app.utils import oauth2
from app.schema.map_search import MapSearchOut
from app.services.suggestions import get_friend_suggestions
from app.schema.suggestions import SuggestionsOut, SuggestionUser
from app.schema.friendships import FriendsOut
from app.schema.our_base_model import OurBaseOut
from app.schema.pagination import UserSearchOut
from app.services import friendships as friendship_service

router = APIRouter()


@router.get("/Friends/search", response_model=MapSearchOut, status_code=status.HTTP_200_OK)
def search_friends(
    q: str | None = None,
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    return friendship_service.search_friends(
        db,
        current_user.user_id,
        q,
        page_number,
        page_size,
    )


@router.get("/Friends/me", response_model=FriendsOut, status_code=status.HTTP_200_OK)
def get_my_friends(
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
):
    return friendship_service.get_my_friends(
        db,
        current_user.user_id,
        page_number,
        page_size,
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
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve suggestions",
        )

    return SuggestionsOut(
        status_code=status.HTTP_200_OK,
        message="Suggestions retrieved successfully",
        data=data,
    )


@router.get(
    "/users/search",
    response_model=UserSearchOut,
    status_code=status.HTTP_200_OK,
)
def search_users(
    query: str,
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    return friendship_service.search_users(
        db,
        current_user.user_id,
        query,
        page_number,
        page_size,
    )


@router.delete("/Friends/{friend_id}", response_model=OurBaseOut, status_code=status.HTTP_200_OK)
def delete_friend(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    return friendship_service.delete_friend(
        db,
        current_user.user_id,
        friend_id,
    )
