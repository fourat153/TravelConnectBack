from enum import Enum


class NotificationStatus(str, Enum):
    seen = "seen"
    not_seen = "not_seen"