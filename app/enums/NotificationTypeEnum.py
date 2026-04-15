import enum


class NotificationTypeEnum(str, enum.Enum):
    friendship = "friendship"
    post_like = "post_like"
    comment_like = "comment_like"
    comment = "comment"
    trip_partner = "trip_partner"
