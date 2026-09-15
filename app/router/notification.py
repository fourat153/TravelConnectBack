from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from Dbengin import get_db
from app.enums import NotificationType
from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.schema.auth import TokenData
from app.schema.devicetoken import DeviceTokenCreate, DeviceTokenOut
from app.schema.notification import NotificationOut
from app.services.notification import NotificationError
from app.services.notification_service import create_and_send_notification
from app.utils.oauth2 import get_current_user

router = APIRouter(prefix="/notifications")


@router.get("", response_model=list[NotificationOut])
def get_notifications(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Notification)
        .where(Notification.recipient_id == current_user.user_id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
    ).all()


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_as_read(
    notification_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notification = db.scalar(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.recipient_id == current_user.user_id,
        )
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    if not notification.is_read:
        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(notification)

    return notification


@router.post("/device-token", response_model=DeviceTokenOut)
def register_device_token(
    data: DeviceTokenCreate,
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = db.execute(
        select(DeviceToken).where(
            DeviceToken.token == data.token
        )
    )

    device_token = result.scalar_one_or_none()

    if device_token:
        device_token.user_id = current_user.user_id
        device_token.updated_at = datetime.now(timezone.utc)
    else:
        device_token = DeviceToken(
            user_id=current_user.user_id,
            token=data.token,
        )

        db.add(device_token)

    db.commit()
    db.refresh(device_token)

    return device_token


@router.post("/test")
def send_test_notification(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = create_and_send_notification(
            db=db,
            recipient_id=current_user.user_id,
            notification_type=NotificationType.POST_COMMENT,
            title="Travel Connect",
            body="This is a test notification!",
        )
    except NotificationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if not result["message_ids"]:
        raise HTTPException(
            status_code=404,
            detail="No device token is registered for the current user.",
        )

    return {
        "message": "Test notification created and sent.",
        "notification_id": result["notification"].id,
        "message_ids": result["message_ids"],
    }


    
