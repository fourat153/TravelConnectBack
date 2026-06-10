import os
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Dbengin import get_db
from app.enums.account_status_enum import AccountStatusEnum
from app.enums.confirmed import ConfirmedEnum
from app.enums.gender_enum import GenderEnum
from app.enums.friendship_status import FriendshipStatusEnum
from app.enums.onboarding import Onboarding
from app.models.city import City
from app.models.comment import Comment
from app.models.Friendship import Friendship
from app.models.FriendshipRequest import FriendshipRequest
from app.models.FriendshipStatus import FriendshipStatus
from app.models.image import Image
from app.models.post import Post
from app.models.post_like import PostLike
from app.models.stop import Stop
from app.models.trip import Trip
from app.models.user import User
from app.utils.general_util import hash_password

router = APIRouter(prefix="/seed", tags=["seed"])

ALLOWED_ENVIRONMENTS = {"development", "dev", "testing", "test", "local"}
CURRENT_USER_EMAIL = "ahmedliouane0@gmail.com"
DEFAULT_AVATAR = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=400&q=80"

SEED_USERS = [
    {
        "email": "admin@travelconnect.dev",
        "password": "Admin123!",
        "firstname": "Maya",
        "lastname": "Grant",
        "gender": GenderEnum.female,
        "profile_picture": "https://images.unsplash.com/photo-1524504388940-b1c1722653e1?auto=format&fit=crop&w=400&q=80",
    },
    {
        "email": "emma.wilson@travelconnect.dev",
        "password": "Travel123!",
        "firstname": "Emma",
        "lastname": "Wilson",
        "gender": GenderEnum.female,
        "profile_picture": "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&w=400&q=80",
    },
    {
        "email": "noah.patel@travelconnect.dev",
        "password": "Travel123!",
        "firstname": "Noah",
        "lastname": "Patel",
        "gender": GenderEnum.male,
        "profile_picture": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=400&q=80",
    },
    {
        "email": "olivia.chen@travelconnect.dev",
        "password": "Travel123!",
        "firstname": "Olivia",
        "lastname": "Chen",
        "gender": GenderEnum.female,
        "profile_picture": "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?auto=format&fit=crop&w=400&q=80",
    },
    {
        "email": "liam.brooks@travelconnect.dev",
        "password": "Travel123!",
        "firstname": "Liam",
        "lastname": "Brooks",
        "gender": GenderEnum.male,
        "profile_picture": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?auto=format&fit=crop&w=400&q=80",
    },
]

SEED_CITIES = [
    {"name": "Paris", "lat": 48.8566, "long": 2.3522},
    {"name": "Tokyo", "lat": 35.6762, "long": 139.6503},
    {"name": "Rome", "lat": 41.9028, "long": 12.4964},
    {"name": "Barcelona", "lat": 41.3874, "long": 2.1686},
    {"name": "Lisbon", "lat": 38.7223, "long": -9.1393},
    {"name": "Cape Town", "lat": -33.9249, "long": 18.4241},
    {"name": "New York", "lat": 40.7128, "long": -74.0060},
    {"name": "Vancouver", "lat": 49.2827, "long": -123.1207},
    {"name": "Marrakech", "lat": 31.6295, "long": -7.9811},
    {"name": "Reykjavik", "lat": 64.1466, "long": -21.9426},
    {"name": "Bali", "lat": -8.4095, "long": 115.1889},
    {"name": "Sydney", "lat": -33.8688, "long": 151.2093},
]

TRIP_TITLES = [
    "A Slow Week in Kyoto",
    "Golden Hours in Lisbon",
    "Weekend Cafes in Paris",
    "Street Food Trail Through Tokyo",
    "Coastal Escape in Barcelona",
    "Cape Town by Sea and Table Mountain",
    "City Lights and Museums in New York",
    "Scenic Mountain Air in Vancouver",
    "Color and Spice Across Marrakech",
    "Volcanic Landscapes in Reykjavik",
    "Island Days in Bali",
]

TRIP_DESCRIPTIONS = [
    "A calm, photo-friendly trip filled with walking tours, local food, and unhurried evenings.",
    "A bright city break focused on neighborhoods, viewpoints, and great coffee stops.",
    "An easygoing itinerary with museums, markets, and long sunset walks.",
    "A food-first trip with street stalls, night markets, and scenic neighborhoods.",
    "A coastal getaway mixing beaches, architecture, and relaxed daily exploring.",
    "A blend of scenic drives, iconic landmarks, and memorable local experiences.",
    "A classic urban escape with skyline views, parks, and late-night dining.",
    "A nature-leaning city trip with waterfronts, trails, and scenic viewpoints.",
    "A vibrant journey through souks, rooftops, and warm desert evenings.",
    "A dramatic northern escape with lagoons, hot springs, and wide-open roads.",
    "A tropical stay focused on temples, beaches, and sunrise adventures.",
]

IMAGE_URLS = [
    "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1469796466635-455ede028aca?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1483683804023-6ccdb62f86ef?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1527631746610-bca00a040d60?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1544976959-9f7c6b0b3b07?auto=format&fit=crop&w=1200&q=80",
]

STOP_TEMPLATES = [
    ("Morning coffee in {city}", "Start the day slowly with a local coffee stop and a relaxed neighborhood walk."),
    ("Sunset viewpoint at {city}", "Catch the best light from a scenic overlook before heading to dinner."),
    ("Local market wander in {city}", "Browse produce, snacks, and handmade goods in a busy neighborhood market."),
    ("Historic streets of {city}", "Spend the afternoon exploring old streets, landmarks, and small museums."),
    ("Harbor walk in {city}", "Take an easy waterfront walk with plenty of photo stops and fresh air."),
]

COMMENT_TEMPLATES = [
    "This route looks perfect for a relaxed day of exploring.",
    "The photos make me want to book a trip right now.",
    "Great mix of food, views, and local spots here.",
    "This itinerary feels super well paced and realistic.",
    "I’d definitely add this place to my travel list.",
    "The sunset shot is incredible.",
    "Love how varied this trip feels from start to finish.",
]


def _current_environment() -> str:
    environment = (
        os.getenv("APP_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("FASTAPI_ENV")
        or os.getenv("PYTHON_ENV")
        or "development"
    ).strip().lower()
    return environment


def _ensure_seed_allowed() -> None:
    environment = _current_environment()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seeding is allowed only in development or testing environments.",
        )


def _seed_user_rows(db: Session) -> tuple[int, dict[str, User]]:
    created = {}
    created_count = 0
    for seed in SEED_USERS:
        user = db.query(User).filter(User.email == seed["email"]).first()
        if user:
            created[seed["email"]] = user
            continue

        user = User(
            email=seed["email"],
            password=hash_password(seed["password"]),
            firstname=seed["firstname"],
            lastname=seed["lastname"],
            gender=seed["gender"],
            status=AccountStatusEnum.active,
            is_confirmed=ConfirmedEnum.Confirmed,
            has_completed_onboarding=Onboarding.Onboarded,
            profile_picture=seed["profile_picture"],
        )
        db.add(user)
        db.flush()
        created_count += 1
        created[seed["email"]] = user

    db.commit()
    return created_count, created


def _seed_city_rows(db: Session) -> tuple[int, dict[str, City]]:
    created = {}
    created_count = 0
    for seed in SEED_CITIES:
        city = db.query(City).filter(City.lat == seed["lat"], City.long == seed["long"]).first()
        if city:
            created[seed["name"]] = city
            continue

        city = City(lat=seed["lat"], long=seed["long"])
        db.add(city)
        db.flush()
        created_count += 1
        created[seed["name"]] = city

    db.commit()
    return created_count, created


def _seed_friendship_status_rows(db: Session) -> tuple[int, dict[str, FriendshipStatus]]:
    created = {}
    created_count = 0

    for status_name in FriendshipStatusEnum:
        status_row = db.query(FriendshipStatus).filter(FriendshipStatus.name == status_name).first()
        if status_row:
            created[status_name.value] = status_row
            continue

        status_row = FriendshipStatus(name=status_name)
        db.add(status_row)
        db.flush()
        created_count += 1
        created[status_name.value] = status_row

    db.commit()
    return created_count, created


def _seed_friendship_rows(db: Session, users: dict[str, User], current_user_email: str = CURRENT_USER_EMAIL) -> int:
    created_count = 0
    accepted_status = (
        db.query(FriendshipStatus)
        .filter(FriendshipStatus.name == FriendshipStatusEnum.accepted)
        .first()
    )

    if not accepted_status:
        accepted_status = FriendshipStatus(name=FriendshipStatusEnum.accepted)
        db.add(accepted_status)
        db.flush()

    current_user = users.get(current_user_email) or db.query(User).filter(User.email == current_user_email).first()
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Current user '{current_user_email}' was not found in the database.",
        )

    friendship_partner_emails = [seed["email"] for seed in SEED_USERS if seed["email"] != current_user_email]

    for partner_email in friendship_partner_emails:
        partner_user = users[partner_email]

        sender_id, receiver_id = sorted((current_user.id, partner_user.id))

        friend_request = db.query(FriendshipRequest).filter(
            FriendshipRequest.sender_id == sender_id,
            FriendshipRequest.receiver_id == receiver_id,
        ).first()
        if not friend_request:
            db.add(
                FriendshipRequest(
                    sender_id=sender_id,
                    receiver_id=receiver_id,
                    status_id=accepted_status.id,
                )
            )

        user_1_id, user_2_id = sender_id, receiver_id
        friendship = db.query(Friendship).filter(
            Friendship.user_1_id == user_1_id,
            Friendship.user_2_id == user_2_id,
        ).first()
        if friendship:
            continue

        db.add(Friendship(user_1_id=user_1_id, user_2_id=user_2_id))
        created_count += 1

    db.commit()
    return created_count


def _seed_trip_rows(db: Session, users: dict[str, User]) -> tuple[int, dict[int, Trip]]:
    created = {}
    created_count = 0
    trip_index = 0
    base_created_at = datetime.utcnow() - timedelta(days=240)
    trips_per_user = [3, 2, 2, 2, 2]

    for user_seed, trip_count in zip(SEED_USERS, trips_per_user, strict=False):
        user = users[user_seed["email"]]
        for _ in range(trip_count):
            title = TRIP_TITLES[trip_index]
            trip = db.query(Trip).filter(Trip.user_id == user.id, Trip.title == title).first()
            if trip:
                created[trip.id] = trip
                trip_index += 1
                continue

            trip = Trip(
                user_id=user.id,
                title=title,
                created_at=base_created_at + timedelta(days=trip_index * 11),
            )
            db.add(trip)
            db.flush()
            created_count += 1
            created[trip.id] = trip
            trip_index += 1

    db.commit()
    return created_count, created


def _seed_stop_rows(db: Session, trips: dict[int, Trip], cities: dict[str, City]) -> tuple[int, dict[int, Stop]]:
    created = {}
    created_count = 0
    city_list = [cities[item["name"]] for item in SEED_CITIES]
    city_cursor = 0

    for trip_number, trip in enumerate(trips.values()):
        stop_count = 3 + (trip_number % 3)
        first_city_id = None
        for stop_order in range(1, stop_count + 1):
            city = city_list[city_cursor % len(city_list)]
            city_cursor += 1
            title_template, description = STOP_TEMPLATES[(trip_number + stop_order) % len(STOP_TEMPLATES)]
            title = title_template.format(city=_city_label(city))

            stop = (
                db.query(Stop)
                .filter(Stop.trip_id == trip.id, Stop.order == stop_order)
                .first()
            )
            if stop:
                created[stop.id] = stop
                if first_city_id is None:
                    first_city_id = stop.city_id
                continue

            stop = Stop(
                trip_id=trip.id,
                city_id=city.id,
                title=title,
                description=description,
                order=stop_order,
            )
            db.add(stop)
            db.flush()
            created_count += 1
            created[stop.id] = stop
            if first_city_id is None:
                first_city_id = city.id

        if trip.city_id is None and first_city_id is not None:
            trip.city_id = first_city_id

    db.commit()
    return created_count, created


def _seed_post_rows(db: Session, stops: dict[int, Stop]) -> tuple[int, dict[int, Post]]:
    created = {}
    created_count = 0
    post_index = 0
    base_created_at = datetime.utcnow() - timedelta(days=120)

    ordered_stops = list(stops.values())
    for stop_number, stop in enumerate(ordered_stops):
        post_count = 1 + (stop_number % 2)
        for post_number in range(1, post_count + 1):
            title = f"{stop.title} - travel journal note {post_number}"
            post = (
                db.query(Post)
                .filter(Post.stop_id == stop.id, Post.title == title)
                .first()
            )
            if post:
                created[post.id] = post
                post_index += 1
                continue

            post = Post(
                stop_id=stop.id,
                title=title,
                created_at=base_created_at + timedelta(days=post_index * 3),
            )
            db.add(post)
            db.flush()
            created_count += 1
            created[post.id] = post
            post_index += 1

    db.commit()
    return created_count, created


def _seed_image_rows(db: Session, posts: dict[int, Post]) -> int:
    created = 0
    for post_index, post in enumerate(posts.values()):
        image_count = 2 + (post_index % 2)
        for image_number in range(image_count):
            link = IMAGE_URLS[(post_index + image_number) % len(IMAGE_URLS)]
            image = (
                db.query(Image)
                .filter(Image.post_id == post.id, Image.link == link)
                .first()
            )
            if image:
                continue

            db.add(
                Image(
                    post_id=post.id,
                    link=link,
                    caption=f"{post.title} photo {image_number + 1}",
                )
            )
            created += 1

    db.commit()
    return created


def _seed_like_rows(db: Session, users: dict[str, User], posts: dict[int, Post]) -> int:
    created = 0
    user_list = list(users.values())
    rng = random.Random(20240606)

    for post_index, post in enumerate(posts.values()):
        trip = post.stop.trip if post.stop else None
        excluded_user_id = trip.user_id if trip else None
        available_users = [user for user in user_list if user.id != excluded_user_id]
        if not available_users:
            available_users = user_list

        like_count = 1 + (post_index % min(3, len(available_users)))
        chosen_users = rng.sample(available_users, k=like_count)

        for user in chosen_users:
            like = (
                db.query(PostLike)
                .filter(PostLike.post_id == post.id, PostLike.user_id == user.id)
                .first()
            )
            if like:
                continue

            db.add(PostLike(post_id=post.id, user_id=user.id))
            created += 1

    db.commit()
    return created


def _seed_comment_rows(db: Session, users: dict[str, User], posts: dict[int, Post]) -> int:
    created = 0
    user_list = list(users.values())
    rng = random.Random(20240606)

    for post_index, post in enumerate(posts.values()):
        trip = post.stop.trip if post.stop else None
        excluded_user_id = trip.user_id if trip else None
        available_users = [user for user in user_list if user.id != excluded_user_id]
        if len(available_users) < 2:
            available_users = user_list

        comment_count = 2 + (post_index % 2)
        chosen_users = rng.sample(available_users, k=min(comment_count, len(available_users)))

        for comment_index, user in enumerate(chosen_users):
            content = COMMENT_TEMPLATES[(post_index + comment_index) % len(COMMENT_TEMPLATES)]
            comment = (
                db.query(Comment)
                .filter(Comment.post_id == post.id, Comment.user_id == user.id, Comment.content == content)
                .first()
            )
            if comment:
                continue

            db.add(Comment(post_id=post.id, user_id=user.id, content=content))
            created += 1

    db.commit()
    return created


def _city_label(city: City) -> str:
    for seed in SEED_CITIES:
        if seed["lat"] == city.lat and seed["long"] == city.long:
            return seed["name"]
    return "Featured City"


def _seed_users_and_related(db: Session) -> tuple[dict[str, User], dict[str, City], dict[int, Trip], dict[int, Stop], dict[int, Post]]:
    _, users = _seed_user_rows(db)
    _, cities = _seed_city_rows(db)
    _, trips = _seed_trip_rows(db, users)
    _, stops = _seed_stop_rows(db, trips, cities)
    _, posts = _seed_post_rows(db, stops)
    return users, cities, trips, stops, posts


@router.post("/users")
def seed_users(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    created_count, _ = _seed_user_rows(db)
    return {"message": "Users seeded successfully", "created": created_count}


@router.post("/trips")
def seed_trips(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    created_count, _ = _seed_trip_rows(db, users)
    return {"message": "Trips seeded successfully", "created": created_count}


@router.post("/cities")
def seed_cities(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    created_count, _ = _seed_city_rows(db)
    return {"message": "Cities seeded successfully", "created": created_count}


@router.post("/friends")
def seed_friends(
    db: Session = Depends(get_db),
    current_user_email: str = CURRENT_USER_EMAIL,
):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    statuses_created, _ = _seed_friendship_status_rows(db)
    friendships_created = _seed_friendship_rows(db, users, current_user_email=current_user_email)
    return {
        "message": "Friends seeded successfully",
        "created": friendships_created,
        "friendship_statuses_created": statuses_created,
    }


@router.post("/stops")
def seed_stops(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    _, cities = _seed_city_rows(db)
    _, trips = _seed_trip_rows(db, users)
    created_count, _ = _seed_stop_rows(db, trips, cities)
    return {"message": "Stops seeded successfully", "created": created_count}


@router.post("/posts")
def seed_posts(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    _, cities = _seed_city_rows(db)
    _, trips = _seed_trip_rows(db, users)
    _, stops = _seed_stop_rows(db, trips, cities)
    created_count, _ = _seed_post_rows(db, stops)
    return {"message": "Posts seeded successfully", "created": created_count}


@router.post("/images")
def seed_images(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    _, cities = _seed_city_rows(db)
    _, trips = _seed_trip_rows(db, users)
    _, stops = _seed_stop_rows(db, trips, cities)
    _, posts = _seed_post_rows(db, stops)
    created = _seed_image_rows(db, posts)
    return {"message": "Images seeded successfully", "created": created}


@router.post("/likes")
def seed_likes(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    _, cities = _seed_city_rows(db)
    _, trips = _seed_trip_rows(db, users)
    _, stops = _seed_stop_rows(db, trips, cities)
    _, posts = _seed_post_rows(db, stops)
    created = _seed_like_rows(db, users, posts)
    return {"message": "Likes seeded successfully", "created": created}


@router.post("/comments")
def seed_comments(db: Session = Depends(get_db)):
    _ensure_seed_allowed()
    _, users = _seed_user_rows(db)
    _, cities = _seed_city_rows(db)
    _, trips = _seed_trip_rows(db, users)
    _, stops = _seed_stop_rows(db, trips, cities)
    _, posts = _seed_post_rows(db, stops)
    created = _seed_comment_rows(db, users, posts)
    return {"message": "Comments seeded successfully", "created": created}


@router.post("/seed_all")
def seed_all(
    db: Session = Depends(get_db),
    current_user_email: str = CURRENT_USER_EMAIL,
):
    _ensure_seed_allowed()
    users_created, users = _seed_user_rows(db)
    friendship_statuses_created, _ = _seed_friendship_status_rows(db)
    friendships_created = _seed_friendship_rows(db, users, current_user_email=current_user_email)
    trips_created, trips = _seed_trip_rows(db, users)
    cities_created, cities = _seed_city_rows(db)
    stops_created, stops = _seed_stop_rows(db, trips, cities)
    posts_created, posts = _seed_post_rows(db, stops)
    images_created = _seed_image_rows(db, posts)
    likes_created = _seed_like_rows(db, users, posts)
    comments_created = _seed_comment_rows(db, users, posts)

    return {
        "message": "Database seeded successfully",
        "summary": {
            "users_created": users_created,
            "friendship_statuses_created": friendship_statuses_created,
            "friendships_created": friendships_created,
            "cities_created": cities_created,
            "trips_created": trips_created,
            "stops_created": stops_created,
            "posts_created": posts_created,
            "images_created": images_created,
            "likes_created": likes_created,
            "comments_created": comments_created,
        },
    }