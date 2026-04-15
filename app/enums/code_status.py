from enum import Enum

class CodeStatus(Enum):
    pending = "pending"
    used = "used"
    expired = "expired"