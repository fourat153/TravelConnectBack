from datetime import datetime

from app.enums import NotificationType
from app.schema.our_base_model import OurBaseModel


class NotificationOut(OurBaseModel):
    id: int
    recipient_id: int
    actor_id: int | None = None
    trip_id: int | None = None
    post_id: int | None = None
    type: NotificationType
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime