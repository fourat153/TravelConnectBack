from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status

from ..database import get_db
from app.utils import oauth2
from app import models
from app.schema.friendships import FriendshipRequestCreate, FriendshipRequestOut

router = APIRouter()


@router.post("/friendship-requests", response_model=FriendshipRequestOut, status_code=status.HTTP_201_CREATED)
def send_friend_request(
    entry: FriendshipRequestCreate,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
):
    if current_user.user_id == entry.receiver_id:
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="You cannot send a request to yourself.",
        )

    existing_request = db.query(models.FriendshipRequest).filter(
        (
            (models.FriendshipRequest.sender_id == current_user.user_id) &
            (models.FriendshipRequest.receiver_id == entry.receiver_id)
        ) | (
            (models.FriendshipRequest.sender_id == entry.receiver_id) &
            (models.FriendshipRequest.receiver_id == current_user.user_id)
        )
    ).first()

    if existing_request:
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="A request already exists between these users.",
        )

    existing_friendship = db.query(models.Friendship).filter(
     (  
        (models.Friendship.user_1_id == current_user.user_id) &
        (models.Friendship.user_2_id == entry.receiver_id)
     )
     |
     (
        (models.Friendship.user_1_id == entry.receiver_id) &
        (models.Friendship.user_2_id == current_user.user_id)
     )
    ).first()

    if existing_friendship:
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="You are already friends with this user.",
        )

    pending_status = db.query(models.FriendshipStatus).filter(
        models.FriendshipStatus.name == "pending"
    ).first()

    try:
        friend_request = models.FriendshipRequest(
            sender_id   = current_user.user_id,
            receiver_id = entry.receiver_id,
            status_id   = pending_status.id,
        )
        db.add(friend_request)
        db.commit()
        db.refresh(friend_request)
    except Exception as e:
        db.rollback()
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
        )

    return FriendshipRequestOut(
        **friend_request.__dict__,
        status_code=status.HTTP_201_CREATED,
        message="Friend request sent successfully.",
    )


@router.patch("/friendship-requests/{request_id}/accept", response_model=FriendshipRequestOut, status_code=status.HTTP_200_OK)
def accept_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
):
    friend_request = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.id == request_id
    ).first()

    if not friend_request:
        return FriendshipRequestOut(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Friend request not found.",
        )

    if friend_request.receiver_id != current_user.user_id:
        return FriendshipRequestOut(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Only the receiver can accept this request.",
        )
    accepted_status = db.query(models.FriendshipStatus).filter(
        models.FriendshipStatus.name == "accepted"
    ).first()


    try:
        friendship = models.Friendship(user_1_id=friend_request.sender_id, user_2_id=friend_request.receiver_id)
        friend_request.status_id = accepted_status.id 
        db.add(friendship)
        db.commit()
    except Exception as e:
        db.rollback()
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
        )

    return FriendshipRequestOut(
        status_code=status.HTTP_200_OK,
        message="Friend request accepted.",
    )


@router.delete("/friendship-requests/{request_id}/decline", response_model=FriendshipRequestOut, status_code=status.HTTP_200_OK)
def decline_friend_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(oauth2.get_current_user),
):
    friend_request = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.id == request_id
    ).first()

    if not friend_request:
        return FriendshipRequestOut(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Friend request not found.",
        )

    if current_user.user_id != friend_request.receiver_id:
        return FriendshipRequestOut(
            status_code=status.HTTP_403_FORBIDDEN,
            message="Not authorized to decline this request.",
        )
    refused_status = db.query(models.FriendshipStatus).filter(
        models.FriendshipStatus.name == "refused"
    ).first()


    try:
        friend_request.status_id = refused_status.id
        db.commit()
    except Exception as e:
        db.rollback()
        return FriendshipRequestOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=str(e),
        )

    return FriendshipRequestOut(
        status_code=status.HTTP_200_OK,
        message="Friend request declined.",
    )