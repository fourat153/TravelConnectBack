from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.schema.friendshipsRequest import (
    FriendshipRequestCreate,
    FriendshipRequestOut,
    RelationshipStatusOut,
)
from app.schema.pagination import IncomingFriendshipRequestsOut
from app.services import friendship_requests as friendship_request_service
from app.utils import oauth2

router = APIRouter()


def _request_response(friend_request: models.FriendshipRequest) -> FriendshipRequestOut:
    return FriendshipRequestOut(
        id=friend_request.id,
        sender_id=friend_request.sender_id,
        receiver_id=friend_request.receiver_id,
        status=friend_request.status.name.value,
    )


@router.post(
    "/friendship-requests",
    response_model=FriendshipRequestOut,
    status_code=status.HTTP_201_CREATED,
)
def send_friend_request(
    entry: FriendshipRequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    friend_request = friendship_request_service.send_friend_request(
        db,
        entry,
        current_user.user_id,
    )
    return _request_response(friend_request)


@router.patch(
    "/friend-requests/{request_id}/accept",
    response_model=FriendshipRequestOut,
)
@router.patch(
    "/friendship-requests/{request_id}/accept",
    response_model=FriendshipRequestOut,
    include_in_schema=False,
)
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    friend_request = friendship_request_service.accept_friend_request(
        db,
        request_id,
        current_user.user_id,
    )
    return _request_response(friend_request)


@router.patch(
    "/friend-requests/{request_id}/decline",
    response_model=FriendshipRequestOut,
)
@router.delete(
    "/friendship-requests/{request_id}/decline",
    response_model=FriendshipRequestOut,
    include_in_schema=False,
)
def decline_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    friend_request = friendship_request_service.decline_friend_request(
        db,
        request_id,
        current_user.user_id,
    )
    return _request_response(friend_request)


@router.get(
    "/friend-requests/incoming",
    response_model=IncomingFriendshipRequestsOut,
)
def get_incoming_friend_requests(
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    return friendship_request_service.get_incoming_friend_requests(
        db,
        current_user.user_id,
        page_number,
        page_size,
    )


@router.get(
    "/friendship-status/{user_id}",
    response_model=RelationshipStatusOut,
)
def get_relationship_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    return friendship_request_service.get_relationship_status(
        db,
        user_id,
        current_user.user_id,
    )
