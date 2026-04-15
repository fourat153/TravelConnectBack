import enum


class AccountStatusEnum(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
