import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models
from app.database import get_db
from app.enums import FriendshipStatusEnum, NotificationType
from app.schema.friendshipsRequest import (
    FriendshipRequestCreate,
    FriendshipRequestOut,
    IncomingFriendshipRequestOut,
    RelationshipStatusOut,
)
from app.services.notification import NotificationError
from app.services.notification_service import create_and_send_notification
from app.utils import oauth2

router = APIRouter()
logger = logging.getLogger(__name__)


def _status(db: Session, name: FriendshipStatusEnum) -> models.FriendshipStatus:
    friendship_status = db.query(models.FriendshipStatus).filter(
        models.FriendshipStatus.name == name
    ).one_or_none()
    if friendship_status is None:
        raise HTTPException(status_code=500, detail="Friendship status is not configured.")
    return friendship_status


def _friendship_exists(db: Session, user_id: int, other_user_id: int) -> bool:
    return db.query(models.Friendship).filter(
        or_(
            (models.Friendship.user_1_id == user_id)
            & (models.Friendship.user_2_id == other_user_id),
            (models.Friendship.user_1_id == other_user_id)
            & (models.Friendship.user_2_id == user_id),
        )
    ).first() is not None


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
    if current_user.user_id == entry.receiver_id:
        raise HTTPException(status_code=400, detail="You cannot send a request to yourself.")

    receiver = db.query(models.User).filter(models.User.id == entry.receiver_id).one_or_none()
    if receiver is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if _friendship_exists(db, current_user.user_id, entry.receiver_id):
        raise HTTPException(status_code=409, detail="You are already friends with this user.")

    pending_status = _status(db, FriendshipStatusEnum.pending)
    existing_request = db.query(models.FriendshipRequest).filter(
        or_(
            (models.FriendshipRequest.sender_id == current_user.user_id)
            & (models.FriendshipRequest.receiver_id == entry.receiver_id),
            (models.FriendshipRequest.sender_id == entry.receiver_id)
            & (models.FriendshipRequest.receiver_id == current_user.user_id),
        ),
    ).first()
    if existing_request is not None and existing_request.status_id == pending_status.id:
        raise HTTPException(
            status_code=409,
            detail="A pending friend request already exists between these users.",
        )

    if existing_request is not None:
        if existing_request.status.name != FriendshipStatusEnum.refused:
            raise HTTPException(status_code=409, detail="A friend request already exists between these users.")
        friend_request = existing_request
        friend_request.sender_id = current_user.user_id
        friend_request.receiver_id = entry.receiver_id
        friend_request.status_id = pending_status.id
    else:
        friend_request = models.FriendshipRequest(
            sender_id=current_user.user_id,
            receiver_id=entry.receiver_id,
            status_id=pending_status.id,
        )
        db.add(friend_request)
    db.commit()
    db.refresh(friend_request)

    sender = db.query(models.User).filter(models.User.id == current_user.user_id).one()
    try:
        create_and_send_notification(
            db=db,
            recipient_id=receiver.id,
            notification_type=NotificationType.FRIEND_REQUEST,
            title="Friend request",
            body=f"{sender.firstname} {sender.lastname} sent you a friend request",
            actor_id=sender.id,
            sender_id=sender.id,
        )
    except NotificationError as exc:
        logger.error("Failed to send friend request notification: %s", exc.detail)
    except Exception:
        logger.exception("Failed to send friend request notification")

    return _request_response(friend_request)


def _get_recipient_request(
    request_id: int, db: Session, current_user_id: int
) -> models.FriendshipRequest:
    friend_request = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.id == request_id
    ).one_or_none()
    if friend_request is None:
        raise HTTPException(status_code=404, detail="Friend request not found.")
    if friend_request.receiver_id != current_user_id:
        raise HTTPException(
            status_code=403,
            detail="Only the recipient can perform this action.",
        )
    return friend_request


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
    friend_request = _get_recipient_request(request_id, db, current_user.user_id)
    if friend_request.status.name != FriendshipStatusEnum.pending:
        raise HTTPException(status_code=409, detail="This friend request is no longer pending.")

    accepted_status = _status(db, FriendshipStatusEnum.accepted)
    user_1_id, user_2_id = sorted((friend_request.sender_id, friend_request.receiver_id))
    if not _friendship_exists(db, user_1_id, user_2_id):
        db.add(models.Friendship(user_1_id=user_1_id, user_2_id=user_2_id))
    friend_request.status_id = accepted_status.id
    db.commit()
    db.refresh(friend_request)

    recipient = db.query(models.User).filter(models.User.id == current_user.user_id).one()
    try:
        create_and_send_notification(
            db=db,
            recipient_id=friend_request.sender_id,
            notification_type=NotificationType.FRIEND_REQUEST_ACCEPTED,
            title="Friend request accepted",
            body=f"{recipient.firstname} {recipient.lastname} accepted your friend request",
            actor_id=recipient.id,
            sender_id=recipient.id,
        )
    except NotificationError as exc:
        logger.error("Failed to send friend request accepted notification: %s", exc.detail)
    except Exception:
        logger.exception("Failed to send friend request accepted notification")

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
    friend_request = _get_recipient_request(request_id, db, current_user.user_id)
    if friend_request.status.name != FriendshipStatusEnum.pending:
        raise HTTPException(status_code=409, detail="This friend request is no longer pending.")
    friend_request.status_id = _status(db, FriendshipStatusEnum.refused).id
    db.commit()
    db.refresh(friend_request)
    return _request_response(friend_request)


@router.get(
    "/friend-requests/incoming",
    response_model=list[IncomingFriendshipRequestOut],
)
def get_incoming_friend_requests(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    pending_status = _status(db, FriendshipStatusEnum.pending)
    requests = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.receiver_id == current_user.user_id,
        models.FriendshipRequest.status_id == pending_status.id,
    ).all()
    return [
        IncomingFriendshipRequestOut(
            id=request.id,
            sender_id=request.sender_id,
            receiver_id=request.receiver_id,
            status=FriendshipStatusEnum.pending.value,
            sender_name=f"{request.sender.firstname} {request.sender.lastname}",
            sender_avatar=request.sender.profile_picture,
        )
        for request in requests
    ]


@router.get(
    "/friendship-status/{user_id}",
    response_model=RelationshipStatusOut,
)
def get_relationship_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    if db.query(models.User).filter(models.User.id == user_id).one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if _friendship_exists(db, current_user.user_id, user_id):
        return RelationshipStatusOut(status="friends")

    pending_status = _status(db, FriendshipStatusEnum.pending)
    request = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.status_id == pending_status.id,
        or_(
            (models.FriendshipRequest.sender_id == current_user.user_id)
            & (models.FriendshipRequest.receiver_id == user_id),
            (models.FriendshipRequest.sender_id == user_id)
            & (models.FriendshipRequest.receiver_id == current_user.user_id),
        ),
    ).first()
    if request is None:
        return RelationshipStatusOut(status="none")
    if request.sender_id == current_user.user_id:
        return RelationshipStatusOut(status="pending_sent")
    return RelationshipStatusOut(status="pending_received")
