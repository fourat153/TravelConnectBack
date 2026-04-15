
import enum

class PrivacyEntityType(str, enum.Enum):
    user = "user"
    trip = "trip"
    stop = "stop"
    post = "post"
 