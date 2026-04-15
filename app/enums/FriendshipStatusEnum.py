import enum


class FriendshipStatusEnum(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"
    refused = "refused"
