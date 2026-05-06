from enum import Enum

class PrivacyType(str , Enum):
    public = "public"
    private = "private" 
    friends_only = "friends_only"