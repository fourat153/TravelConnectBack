from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.enums import PrivacyEntityType, PrivacyType
from app.models import Friendship, Post, PrivacySettings, Stop, Trip, User


def get_privacy_entity_owner_id(
    db: Session,
    entity_type: PrivacyEntityType,
    entity_id: int,
) -> int | None:
    if entity_type == PrivacyEntityType.user:
        entity = db.query(User).filter(User.id == entity_id).first()
        return entity.id if entity else None
    if entity_type == PrivacyEntityType.trip:
        entity = db.query(Trip).filter(Trip.id == entity_id).first()
        return entity.user_id if entity else None
    if entity_type == PrivacyEntityType.stop:
        entity = db.query(Stop).filter(Stop.id == entity_id).first()
        return entity.trip.user_id if entity and entity.trip else None
    if entity_type == PrivacyEntityType.post:
        entity = db.query(Post).filter(Post.id == entity_id).first()
        return (
            entity.stop.trip.user_id
            if entity and entity.stop and entity.stop.trip
            else None
        )
    return None


def can_modify_trip(trip: Trip, actor_id: int) -> bool:
    return trip.user_id == actor_id


def can_modify_stop(stop: Stop, actor_id: int) -> bool:
    return stop.trip is not None and can_modify_trip(stop.trip, actor_id)


def can_create_post_on_stop(stop: Stop, actor_id: int) -> bool:
    return stop.trip is not None and can_modify_trip(stop.trip, actor_id)


def can_delete_post(post: Post, actor_id: int) -> bool:
    return post.user_id == actor_id


def get_friend_ids(db: Session, viewer_id: int) -> set[int]:
    friendships = db.query(Friendship).filter(
        or_(
            Friendship.user_1_id == viewer_id,
            Friendship.user_2_id == viewer_id,
        )
    ).all()

    return {
        friendship.user_2_id
        if friendship.user_1_id == viewer_id
        else friendship.user_1_id
        for friendship in friendships
    }


def load_trip_visibility_data(
    db: Session,
    trips: list[Trip],
    viewer_id: int,
) -> tuple[dict[int, PrivacySettings], set[int]]:
    if not trips:
        return {}, set()

    trip_ids = [trip.id for trip in trips]
    privacy_settings = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.trip,
        PrivacySettings.entity_id.in_(trip_ids),
    ).all()

    privacy_by_trip = {
        setting.entity_id: setting
        for setting in privacy_settings
    }

    return privacy_by_trip, get_friend_ids(db, viewer_id)


def can_view_trip(
    db: Session,
    trip: Trip,
    viewer_id: int,
    friend_ids: set[int] | None = None,
    privacy_by_trip: dict[int, PrivacySettings] | None = None,
) -> bool:
    if trip.user_id == viewer_id:
        return True

    if privacy_by_trip is None:
        setting = db.query(PrivacySettings).filter(
            PrivacySettings.entity_type == PrivacyEntityType.trip,
            PrivacySettings.entity_id == trip.id,
        ).first()
    else:
        setting = privacy_by_trip.get(trip.id)

    if setting is None:
        return False

    try:
        privacy_type = PrivacyType(setting.privacy_type)
    except (TypeError, ValueError):
        return False

    if privacy_type == PrivacyType.public:
        return True

    if privacy_type == PrivacyType.private:
        return False

    if privacy_type != PrivacyType.friends_only:
        return False

    if friend_ids is None:
        friend_ids = get_friend_ids(db, viewer_id)

    return trip.user_id in friend_ids