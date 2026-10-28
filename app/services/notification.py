import logging

from firebase_admin.exceptions import FirebaseError
from firebase_admin import messaging

logger = logging.getLogger(__name__)


class NotificationError(Exception):
    def __init__(self, detail: str, status_code: int):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def send_notification(
    token: str,
    title: str,
    body: str,
    post_id: int | str | None = None,
    trip_id: int | str | None = None,
    actor_id: int | str | None = None,
    sender_id: int | str | None = None,
) -> str:
    try:
        data_payload = {
            "title": str(title),
            "body": str(body),
        }
        if post_id is not None:
            data_payload["post_id"] = str(post_id)
            data_payload["url"] = f"/post/{post_id}"
        if trip_id is not None:
            data_payload["trip_id"] = str(trip_id)
            data_payload["url"] = f"/map?tripId={trip_id}&ownerId={actor_id}"
        if actor_id is not None:
            data_payload["actor_id"] = str(actor_id)
        if sender_id is not None:
            data_payload["sender_id"] = str(sender_id)

        message = messaging.Message(
            data=data_payload,
            token=token,
        )

        return messaging.send(message)
    except ValueError as exc:
        raise NotificationError("The notification data is invalid.", 400) from exc
    except FirebaseError as exc:
        logger.exception(
            "Firebase error: type=%s code=%s message=%s",
            type(exc).__name__,
            exc.code,
            exc,
        )
        if isinstance(exc, messaging.UnregisteredError):
            raise NotificationError(
                "The device token is no longer registered.",
                410,
            ) from exc
        if exc.code in {"invalid-argument", "registration-token-not-registered"}:
            raise NotificationError(f"Firebase error: {exc}", 400) from exc
        raise NotificationError(f"Firebase error: {exc}", 502) from exc
    except Exception as exc:
        logger.exception("Unexpected error while sending notification")
        raise NotificationError("The notification could not be sent.", 500) from exc


