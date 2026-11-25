import logging

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app import models
from app.enums import FriendshipStatusEnum, NotificationType
from app.schema.friendshipsRequest import (
    FriendshipRequestCreate,
    IncomingFriendshipRequestOut,
    RelationshipStatusOut,
)
from app.schema.pagination import IncomingFriendshipRequestsOut
from app.services.notification import NotificationError
from app.services.notification_service import create_and_send_notification
from app.utils.pagination import div_ceil

logger = logging.getLogger(__name__)


def get_status(
    db: Session,
    name: FriendshipStatusEnum,
) -> models.FriendshipStatus:
    friendship_status = db.query(models.FriendshipStatus).filter(
        models.FriendshipStatus.name == name
    ).one_or_none()
    if friendship_status is None:
        raise HTTPException(
            status_code=500,
            detail="Friendship status is not configured.",
        )
    return friendship_status


def friendship_exists(db: Session, user_id: int, other_user_id: int) -> bool:
    return db.query(models.Friendship).filter(
        or_(
            (models.Friendship.user_1_id == user_id)
            & (models.Friendship.user_2_id == other_user_id),
            (models.Friendship.user_1_id == other_user_id)
            & (models.Friendship.user_2_id == user_id),
        )
    ).first() is not None


def get_recipient_request(
    db: Session,
    request_id: int,
    receiver_id: int,
) -> models.FriendshipRequest:
    friend_request = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.id == request_id
    ).one_or_none()
    if friend_request is None:
        raise HTTPException(status_code=404, detail="Friend request not found.")
    if friend_request.receiver_id != receiver_id:
        raise HTTPException(
            status_code=403,
            detail="Only the recipient can perform this action.",
        )
    return friend_request


def send_friend_request(
    db: Session,
    entry: FriendshipRequestCreate,
    sender_id: int,
) -> models.FriendshipRequest:
    if sender_id == entry.receiver_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot send a request to yourself.",
        )

    receiver = db.query(models.User).filter(
        models.User.id == entry.receiver_id
    ).one_or_none()
    if receiver is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if friendship_exists(db, sender_id, entry.receiver_id):
        raise HTTPException(
            status_code=409,
            detail="You are already friends with this user.",
        )

    pending_status = get_status(db, FriendshipStatusEnum.pending)
    existing_request = db.query(models.FriendshipRequest).filter(
        or_(
            (models.FriendshipRequest.sender_id == sender_id)
            & (models.FriendshipRequest.receiver_id == entry.receiver_id),
            (models.FriendshipRequest.sender_id == entry.receiver_id)
            & (models.FriendshipRequest.receiver_id == sender_id),
        ),
    ).first()
    if existing_request is not None and existing_request.status_id == pending_status.id:
        raise HTTPException(
            status_code=409,
            detail="A pending friend request already exists between these users.",
        )

    if existing_request is not None:
        if existing_request.status.name != FriendshipStatusEnum.refused:
            raise HTTPException(
                status_code=409,
                detail="A friend request already exists between these users.",
            )
        friend_request = existing_request
        friend_request.sender_id = sender_id
        friend_request.receiver_id = entry.receiver_id
        friend_request.status_id = pending_status.id
    else:
        friend_request = models.FriendshipRequest(
            sender_id=sender_id,
            receiver_id=entry.receiver_id,
            status_id=pending_status.id,
        )
        db.add(friend_request)

    db.commit()
    db.refresh(friend_request)

    sender = db.query(models.User).filter(models.User.id == sender_id).one()
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
        logger.error(
            "Failed to send friend request notification: %s",
            exc.detail,
        )
    except Exception:
        logger.exception("Failed to send friend request notification")

    return friend_request


def accept_friend_request(
    db: Session,
    request_id: int,
    receiver_id: int,
) -> models.FriendshipRequest:
    friend_request = get_recipient_request(db, request_id, receiver_id)
    if friend_request.status.name != FriendshipStatusEnum.pending:
        raise HTTPException(
            status_code=409,
            detail="This friend request is no longer pending.",
        )

    accepted_status = get_status(db, FriendshipStatusEnum.accepted)
    user_1_id, user_2_id = sorted(
        (friend_request.sender_id, friend_request.receiver_id)
    )
    if not friendship_exists(db, user_1_id, user_2_id):
        db.add(models.Friendship(user_1_id=user_1_id, user_2_id=user_2_id))

    friend_request.status_id = accepted_status.id
    db.commit()
    db.refresh(friend_request)

    recipient = db.query(models.User).filter(
        models.User.id == receiver_id
    ).one()
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
        logger.error(
            "Failed to send friend request accepted notification: %s",
            exc.detail,
        )
    except Exception:
        logger.exception("Failed to send friend request accepted notification")

    return friend_request


def decline_friend_request(
    db: Session,
    request_id: int,
    receiver_id: int,
) -> models.FriendshipRequest:
    friend_request = get_recipient_request(db, request_id, receiver_id)
    if friend_request.status.name != FriendshipStatusEnum.pending:
        raise HTTPException(
            status_code=409,
            detail="This friend request is no longer pending.",
        )

    friend_request.status_id = get_status(
        db,
        FriendshipStatusEnum.refused,
    ).id
    db.commit()
    db.refresh(friend_request)
    return friend_request


def get_relationship_status(
    db: Session,
    user_id: int,
    current_user_id: int,
) -> RelationshipStatusOut:
    if db.query(models.User).filter(models.User.id == user_id).one_or_none() is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if friendship_exists(db, current_user_id, user_id):
        return RelationshipStatusOut(status="friends")

    pending_status = get_status(db, FriendshipStatusEnum.pending)
    request = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.status_id == pending_status.id,
        or_(
            (models.FriendshipRequest.sender_id == current_user_id)
            & (models.FriendshipRequest.receiver_id == user_id),
            (models.FriendshipRequest.sender_id == user_id)
            & (models.FriendshipRequest.receiver_id == current_user_id),
        ),
    ).first()
    if request is None:
        return RelationshipStatusOut(status="none")
    if request.sender_id == current_user_id:
        return RelationshipStatusOut(status="pending_sent")
    return RelationshipStatusOut(status="pending_received")


def get_incoming_friend_requests(
    db: Session,
    receiver_id: int,
    page_number: int,
    page_size: int,
) -> IncomingFriendshipRequestsOut:
    pending_status = get_status(db, FriendshipStatusEnum.pending)
    requests_query = db.query(models.FriendshipRequest).filter(
        models.FriendshipRequest.receiver_id == receiver_id,
        models.FriendshipRequest.status_id == pending_status.id,
    )
    total_records = requests_query.count()
    requests = requests_query.offset((page_number - 1) * page_size).limit(page_size).all()
    return IncomingFriendshipRequestsOut(
        requests=[
            IncomingFriendshipRequestOut(
                id=request.id,
                sender_id=request.sender_id,
                receiver_id=request.receiver_id,
                status=FriendshipStatusEnum.pending.value,
                sender_name=f"{request.sender.firstname} {request.sender.lastname}",
                sender_avatar=request.sender.profile_picture,
            )
            for request in requests
        ],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )
