from .user import router as user_router
from .auth import router as auth_router
from .city import router as city_router
from .trip import router as trip_router
from .stop import router as stop_router
from .privacy_settings import router as privacy_settings_router
from .post import router as posts_router
from .seed import router as seed_router
from .friendships import router as friendships_router
from .friendshipsRequest import router as friendshipsRequest_router


__all__ = ["user_router", "auth_router", "city_router", "trip_router" , "stop_router" , "privacy_settings_router" , "posts_router" , "seed_router" ,"friendships_router" , "friendshipsRequest_router"]