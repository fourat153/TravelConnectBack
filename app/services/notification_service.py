from sqlalchemy import select
from sqlalchemy.orm import Session

from app.enums import NotificationType
from app.models.device_token import DeviceToken
from app.models.notification import Notification
from app.services.notification import NotificationError, send_notification


def create_and_send_notification(
    db: Session,
    recipient_id: int,
    notification_type: NotificationType,
    title: str,
    body: str,
    actor_id: int | None = None,
    post_id: int | None = None,
) -> dict[str, Notification | list[str]]:
    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        post_id=post_id,
        type=notification_type,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    device_tokens = db.scalars(
        select(DeviceToken.token).where(DeviceToken.user_id == recipient_id)
    ).all()

    message_ids = []
    for device_token in device_tokens:
        try:
            message_ids.append(
                send_notification(
                    token=device_token,
                    title=title,
                    body=body,
                    post_id=post_id,
                    actor_id=actor_id,
                )
            )
        except NotificationError as exc:
            if exc.status_code != 410:
                raise
            db.query(DeviceToken).filter(DeviceToken.token == device_token).delete()

    db.commit()

    return {
        "notification": notification,
        "message_ids": message_ids,
    }
