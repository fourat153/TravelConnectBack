"""Seed a small, repeatable demo dataset for local development.

Run from the repository root with:

    python -m scripts.seed

The seeder uses the application's configured database and session factory. It
does not create tables, run migrations, or delete existing data.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Callable, TypeVar

from sqlalchemy import or_
from sqlalchemy.orm import Session

from Dbengin import SessionLocal
from app import models
from app.enums import (
    AccountStatusEnum,
    ConfirmedEnum,
    GenderEnum,
    NotificationType,
    Onboarding,
    PrivacyEntityType,
    PrivacyType,
)
from app.utils.general_util import hash_password


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


DEMO_PASSWORD = "TravelConnectDemo123!"
DEMO_RELATIONSHIP_USER_ID = 26
DEMO_RELATIONSHIP_USER_EMAIL = "ahmedli@yopmail.com"
DEMO_CONTENT_USER_KEYS = frozenset({"alice", "ben", "claire", "diego"})
T = TypeVar("T")


@dataclass(frozen=True)
class DemoUser:
    key: str
    email: str
    firstname: str
    lastname: str
    gender: GenderEnum
    city: str
    profile_picture: str


DEMO_USERS = (
    DemoUser(
        "alice",
        "alice.demo@travelconnect.local",
        "Alice",
        "Morgan",
        GenderEnum.female,
        "London",
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=256&h=256&fit=crop&crop=face",
    ),
    DemoUser(
        "ben",
        "ben.demo@travelconnect.local",
        "Ben",
        "Carter",
        GenderEnum.male,
        "Manchester",
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=256&h=256&fit=crop&crop=face",
    ),
    DemoUser(
        "claire",
        "claire.demo@travelconnect.local",
        "Claire",
        "Dubois",
        GenderEnum.female,
        "Paris",
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=256&h=256&fit=crop&crop=face",
    ),
    DemoUser(
        "diego",
        "diego.demo@travelconnect.local",
        "Diego",
        "Santos",
        GenderEnum.male,
        "Madrid",
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=256&h=256&fit=crop&crop=face",
    ),
    DemoUser(
        "emma",
        "emma.demo@travelconnect.local",
        "Emma",
        "Wilson",
        GenderEnum.female,
        "London",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=256&h=256&fit=crop&crop=face",
    ),
    DemoUser(
        "finn",
        "finn.demo@travelconnect.local",
        "Finn",
        "Anderson",
        GenderEnum.male,
        "Paris",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=256&h=256&fit=crop&crop=face",
    ),
    DemoUser(
        "grace",
        "grace.demo@travelconnect.local",
        "Grace",
        "Taylor",
        GenderEnum.female,
        "Madrid",
        "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=256&h=256&fit=crop&crop=face",
    ),
)


DEMO_CITIES = (
    ("London", 51.5074, -0.1278),
    ("Manchester", 53.4808, -2.2426),
    ("Paris", 48.8566, 2.3522),
    ("Madrid", 40.4168, -3.7038),
    ("Lisbon", 38.7223, -9.1393),
    ("Porto", 41.1579, -8.6291),
    ("Kyoto", 35.0116, 135.7681),
    ("Nara", 34.6851, 135.8048),
    ("Osaka", 34.6937, 135.5023),
    ("Barcelona", 41.3874, 2.1686),
    ("Nice", 43.7102, 7.2620),
)


def _get_or_create(
    db: Session,
    lookup: Callable[[], T | None],
    factory: Callable[[], T],
    label: str,
    counts: dict[str, int],
) -> T:
    existing = lookup()
    if existing is not None:
        counts["skipped"] += 1
        print(f"  - skipped {label}")
        return existing

    record = factory()
    db.add(record)
    db.flush()
    counts["created"] += 1
    print(f"  + created {label}")
    return record


def _seed_cities(db: Session, counts: dict[str, int]) -> dict[str, models.City]:
    cities: dict[str, models.City] = {}
    for name, latitude, longitude in DEMO_CITIES:
        city = _get_or_create(
            db,
            lambda name=name, latitude=latitude, longitude=longitude: db.query(
                models.City
            )
            .filter(
                models.City.name == name,
                models.City.lat == latitude,
                models.City.long == longitude,
            )
            .one_or_none(),
            lambda name=name, latitude=latitude, longitude=longitude: models.City(
                name=name, lat=latitude, long=longitude
            ),
            f"city {name}",
            counts,
        )
        cities[name] = city
    return cities


def _seed_users(
    db: Session, cities: dict[str, models.City], counts: dict[str, int]
) -> dict[str, models.User]:
    users: dict[str, models.User] = {}
    for demo_user in DEMO_USERS:
        user = _get_or_create(
            db,
            lambda email=demo_user.email: db.query(models.User)
            .filter(models.User.email == email)
            .one_or_none(),
            lambda demo_user=demo_user: models.User(
                email=demo_user.email,
                password=hash_password(DEMO_PASSWORD),
                firstname=demo_user.firstname,
                lastname=demo_user.lastname,
                gender=demo_user.gender,
                status=AccountStatusEnum.active,
                is_confirmed=ConfirmedEnum.Confirmed,
                has_completed_onboarding=Onboarding.Onboarded,
                city_id=cities[demo_user.city].id,
                profile_picture=demo_user.profile_picture or None,
            ),
            f"user {demo_user.email}",
            counts,
        )
        if not user.profile_picture:
            user.profile_picture = demo_user.profile_picture
            db.flush()
            counts["updated"] = counts.get("updated", 0) + 1
            print(f"  ~ updated profile picture for {demo_user.email}")
        users[demo_user.key] = user
    return users


def _seed_trips(
    db: Session, users: dict[str, models.User], cities: dict[str, models.City], counts: dict[str, int]
) -> dict[str, models.Trip]:
    trip_specs = (
        ("alice_lisbon", "alice", "Atlantic Weekend: Lisbon to Porto", ("Lisbon", "Porto")),
        ("ben_kyoto", "ben", "Japan Highlights: Kyoto to Osaka", ("Kyoto", "Nara", "Osaka")),
        (
            "claire_mediterranean",
            "claire",
            "Mediterranean Summer: Barcelona to Nice",
            ("Barcelona", "Nice"),
        ),
    )
    trips: dict[str, models.Trip] = {}
    for key, owner_key, title, stop_names in trip_specs:
        trip = _get_or_create(
            db,
            lambda owner_id=users[owner_key].id, title=title: db.query(models.Trip)
            .filter(models.Trip.user_id == owner_id, models.Trip.title == title)
            .one_or_none(),
            lambda owner_id=users[owner_key].id, title=title: models.Trip(
                user_id=owner_id, title=title
            ),
            f"trip {title}",
            counts,
        )
        trips[key] = trip

        privacy = db.query(models.PrivacySettings).filter(
            models.PrivacySettings.entity_type == PrivacyEntityType.trip,
            models.PrivacySettings.entity_id == trip.id,
        ).one_or_none()
        if privacy is None:
            db.add(
                models.PrivacySettings(
                    entity_type=PrivacyEntityType.trip,
                    entity_id=trip.id,
                    privacy_type=PrivacyType.public,
                )
            )
            db.flush()
            counts["created"] += 1
            print(f"  + created public privacy for {title}")
        else:
            counts["skipped"] += 1
            print(f"  - skipped privacy for {title}")

        for order, city_name in enumerate(stop_names, start=1):
            description = f"Explore {city_name} on the {title.lower()} route. 🧭✨"
            stop = db.query(models.Stop).filter(
                models.Stop.trip_id == trip.id,
                models.Stop.order == order,
            ).one_or_none()
            if stop is None:
                db.add(
                    models.Stop(
                        trip_id=trip.id,
                        city_id=cities[city_name].id,
                        title=city_name,
                        description=description,
                        order=order,
                    )
                )
                db.flush()
                counts["created"] += 1
                print(f"  + created stop {title} #{order}")
            elif stop.description != description:
                stop.description = description
                db.flush()
                counts["updated"] += 1
                print(f"  ~ updated stop {title} #{order}")
            else:
                counts["skipped"] += 1
                print(f"  - skipped stop {title} #{order}")
    return trips


def _seed_posts(
    db: Session, users: dict[str, models.User], trips: dict[str, models.Trip], counts: dict[str, int]
) -> dict[str, models.Post]:
    post_specs = (
        (
            "lisbon_arrival",
            "alice_lisbon",
            "alice",
            1,
            "First light in Lisbon 🌅",
            "First light in Lisbon",
            "https://images.unsplash.com/photo-1513635269975-59663e0ac1ad?auto=format&fit=crop&w=1200&q=80",
            "Morning light in Lisbon 🌅",
        ),
        (
            "porto_river",
            "alice_lisbon",
            "alice",
            2,
            "A slow afternoon by the Douro 🚤",
            "A slow afternoon by the Douro",
            "https://images.unsplash.com/photo-1555881400-74d7aca?auto=format&fit=crop&w=1200&q=80",
            "The Douro River in Porto 🚤",
        ),
        (
            "kyoto_temple",
            "ben_kyoto",
            "ben",
            1,
            "Quiet morning in Kyoto ⛩️",
            "Quiet morning in Kyoto",
            "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?auto=format&fit=crop&w=1200&q=80",
            "A quiet Kyoto temple ⛩️",
        ),
        (
            "nara_deer",
            "ben_kyoto",
            "ben",
            2,
            "A peaceful walk through Nara 🦌",
            "A peaceful walk through Nara",
            "https://images.unsplash.com/photo-1528360983277-13d401cdc186?auto=format&fit=crop&w=1200&q=80",
            "A walk through Nara 🦌",
        ),
        (
            "barcelona_food",
            "claire_mediterranean",
            "claire",
            1,
            "Tapas, sunlight, and new friends 🥘☀️",
            "Tapas, sunlight, and new friends",
            "https://images.unsplash.com/photo-1539037116277-4db20889f2d4?auto=format&fit=crop&w=1200&q=80",
            "An evening in Barcelona 🥘",
        ),
        (
            "nice_sunset",
            "claire_mediterranean",
            "claire",
            2,
            "Sunset over the Promenade des Anglais 🌊",
            "Sunset over the Promenade des Anglais",
            "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
            "A Mediterranean sunset 🌊",
        ),
    )
    posts: dict[str, models.Post] = {}
    for (
        key,
        trip_key,
        author_key,
        order,
        title,
        legacy_title,
        image_link,
        image_caption,
    ) in post_specs:
        trip = trips[trip_key]
        stop = db.query(models.Stop).filter(
            models.Stop.trip_id == trip.id,
            models.Stop.order == order,
        ).one()
        post = db.query(models.Post).filter(
            models.Post.stop_id == stop.id,
            models.Post.title.in_((title, legacy_title)),
        ).one_or_none()
        if post is None:
            post = models.Post(stop_id=stop.id, user_id=users[author_key].id, title=title)
            db.add(post)
            db.flush()
            counts["created"] += 1
            print(f"  + created post {title}")
        elif post.title != title:
            post.title = title
            db.flush()
            counts["updated"] += 1
            print(f"  ~ updated post {title}")
        else:
            counts["skipped"] += 1
            print(f"  - skipped post {title}")
        posts[key] = post
        image = db.query(models.Image).filter(
            models.Image.post_id == post.id,
        ).order_by(models.Image.id).first()
        if image is None:
            db.add(
                models.Image(
                    post_id=post.id,
                    link=image_link,
                    caption=image_caption,
                )
            )
            db.flush()
            counts["created"] += 1
            print(f"  + created image for post {title}")
        elif image.link != image_link or image.caption != image_caption:
            image.link = image_link
            image.caption = image_caption
            db.flush()
            counts["updated"] += 1
            print(f"  ~ updated image for post {title}")
        else:
            counts["skipped"] += 1
            print(f"  - skipped image for post {title}")
    return posts


def _seed_friendships(
    db: Session, users: dict[str, models.User], counts: dict[str, int]
) -> None:
    relationship_user = db.query(models.User).filter(
        models.User.id == DEMO_RELATIONSHIP_USER_ID
    ).one_or_none()
    if relationship_user is None:
        raise RuntimeError(
            f"Cannot seed demo relationships: no user exists with id "
            f"{DEMO_RELATIONSHIP_USER_ID}."
        )
    if relationship_user.email != DEMO_RELATIONSHIP_USER_EMAIL:
        raise RuntimeError(
            f"Cannot seed demo relationships: user id {DEMO_RELATIONSHIP_USER_ID} "
            f"is {relationship_user.email!r}, not {DEMO_RELATIONSHIP_USER_EMAIL!r}."
        )

    pairs = (
        ("alice", "ben"),
        ("alice", "claire"),
        ("ben", "diego"),
        ("ahmedli@yopmail.com", "alice"),
        ("ahmedli@yopmail.com", "ben"),
        ("ahmedli@yopmail.com", "claire"),
        ("ahmedli@yopmail.com", "diego"),
    )
    for first, second in pairs:
        first_id = (
            relationship_user.id
            if first == DEMO_RELATIONSHIP_USER_EMAIL
            else users[first].id
        )
        second_id = (
            relationship_user.id
            if second == DEMO_RELATIONSHIP_USER_EMAIL
            else users[second].id
        )
        user_1_id, user_2_id = sorted((first_id, second_id))
        friendship = db.query(models.Friendship).filter(
            or_(
                (models.Friendship.user_1_id == user_1_id)
                & (models.Friendship.user_2_id == user_2_id),
                (models.Friendship.user_1_id == user_2_id)
                & (models.Friendship.user_2_id == user_1_id),
            )
        ).one_or_none()
        if friendship is None:
            db.add(models.Friendship(user_1_id=user_1_id, user_2_id=user_2_id))
            db.flush()
            counts["created"] += 1
            print(f"  + created friendship {first} <-> {second}")
        else:
            counts["skipped"] += 1
            print(f"  - skipped friendship {first} <-> {second}")


def _seed_interactions(
    db: Session, users: dict[str, models.User], posts: dict[str, models.Post], counts: dict[str, int]
) -> None:
    for post_key, post in posts.items():
        for user_key, user in users.items():
            if user_key not in DEMO_CONTENT_USER_KEYS:
                continue
            if user.id == post.user_id:
                continue

            like = db.query(models.PostLike).filter(
                models.PostLike.post_id == post.id,
                models.PostLike.user_id == user.id,
            ).one_or_none()
            if like is None:
                db.add(models.PostLike(post_id=post.id, user_id=user.id))
                db.flush()
                counts["created"] += 1
                print(f"  + created like on {post_key} by {user_key}")
            else:
                counts["skipped"] += 1
                print(f"  - skipped like on {post_key} by {user_key}")

            content = (
                f"{user.firstname} enjoyed this travel moment and added it "
                "to their itinerary. ✈️🌍"
            )
            comment = db.query(models.Comment).filter(
                models.Comment.post_id == post.id,
                models.Comment.user_id == user.id,
            ).order_by(models.Comment.id).first()
            if comment is None:
                db.add(
                    models.Comment(
                        post_id=post.id,
                        user_id=user.id,
                        content=content,
                    )
                )
                db.flush()
                counts["created"] += 1
                print(f"  + created comment on {post_key} by {user_key}")
            elif comment.content != content:
                comment.content = content
                db.flush()
                counts["updated"] += 1
                print(f"  ~ updated comment on {post_key} by {user_key}")
            else:
                counts["skipped"] += 1
                print(f"  - skipped comment on {post_key} by {user_key}")


def _seed_notifications(
    db: Session,
    users: dict[str, models.User],
    posts: dict[str, models.Post],
    counts: dict[str, int],
) -> None:
    notification_specs = (
        ("alice", "ben", "lisbon_arrival", NotificationType.POST_LIKE),
        ("alice", "claire", "lisbon_arrival", NotificationType.POST_COMMENT),
        ("ben", "alice", "kyoto_temple", NotificationType.POST_LIKE),
        ("claire", "diego", "barcelona_food", NotificationType.POST_COMMENT),
    )
    for recipient_key, actor_key, post_key, notification_type in notification_specs:
        post = posts[post_key]
        exists = db.query(models.Notification).filter(
            models.Notification.recipient_id == users[recipient_key].id,
            models.Notification.actor_id == users[actor_key].id,
            models.Notification.post_id == post.id,
            models.Notification.type == notification_type,
        ).one_or_none()
        if exists is None:
            db.add(
                models.Notification(
                    recipient_id=users[recipient_key].id,
                    actor_id=users[actor_key].id,
                    post_id=post.id,
                    trip_id=post.stop.trip_id,
                    type=notification_type,
                    is_read=False,
                )
            )
            db.flush()
            counts["created"] += 1
            print(f"  + created {notification_type.value} notification for {recipient_key}")
        else:
            counts["skipped"] += 1
            print(f"  - skipped notification for {recipient_key}")


def seed() -> dict[str, int]:
    """Populate the configured database and return created/skipped counts."""
    counts = {"created": 0, "skipped": 0, "updated": 0}
    with SessionLocal() as db:
        try:
            with db.begin():
                cities = _seed_cities(db, counts)
                users = _seed_users(db, cities, counts)
                trips = _seed_trips(db, users, cities, counts)
                posts = _seed_posts(db, users, trips, counts)
                _seed_friendships(db, users, counts)
                _seed_interactions(db, users, posts, counts)
                _seed_notifications(db, users, posts, counts)
        except Exception:
            db.rollback()
            print("Seeding failed; all changes from this run were rolled back.")
            raise
    print(
        f"Seeding complete: {counts['created']} created, "
        f"{counts['updated']} updated, {counts['skipped']} skipped."
    )
    return counts


if __name__ == "__main__":
    seed()
