import logging
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.enums import (
    NotificationType,
    PrivacyEntityType,
    PrivacyType,
)
from app.models import City, Friendship, Post, PrivacySettings, Stop, Trip, User
from app.schema.trip import TripCreate
from app.services.notification import NotificationError
from app.services.notification_service import create_and_send_notification
from app.utils.error_handling import exception_handler
from app.services.trip_privacy import (
    can_modify_trip,
    can_view_trip,
    load_trip_visibility_data,
)

logger = logging.getLogger(__name__)


def create_trip(db: Session, entry: TripCreate, user_id: int) -> Trip:
    user = db.query(User).filter(User.id == user_id).first()

    user_profile_privacy = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.user,
        PrivacySettings.entity_id == user.id,
    ).first()
    privacy_type = (
        PrivacyType(entry.privacy)
        if entry.privacy
        else (
            user_profile_privacy.privacy_type
            if user_profile_privacy
            else PrivacyType.public
        )
    )

    try:
        trip = Trip(
            user_id=user_id,
            title=entry.title,
        )
        db.add(trip)
        db.flush()

        trip_privacy = PrivacySettings(
            entity_type=PrivacyEntityType.trip,
            entity_id=trip.id,
            privacy_type=privacy_type,
        )
        db.add(trip_privacy)

        route_points = [
            (entry.from_city, 0),
            (entry.to_city, 1),
        ]

        for city_input, order in route_points:
            city = db.query(City).filter(
                City.lat == city_input.lat,
                City.long == city_input.lon,
            ).first()

            if not city:
                city = City(lat=city_input.lat, long=city_input.lon)
                db.add(city)
                db.flush()

            stop = Stop(
                trip_id=trip.id,
                city_id=city.id,
                title=city_input.label,
                order=order,
            )
            db.add(stop)

        db.commit()
        db.refresh(trip)

    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create trip",
        )

    friends = db.query(Friendship).filter(
        (Friendship.user_1_id == user_id)
        | (Friendship.user_2_id == user_id)
    ).all()
    friend_ids = {
        friendship.user_2_id
        if friendship.user_1_id == user_id
        else friendship.user_1_id
        for friendship in friends
    }
    creator_name = f"{user.firstname} {user.lastname}"
    for friend_id in friend_ids:
        try:
            create_and_send_notification(
                db=db,
                recipient_id=friend_id,
                actor_id=user_id,
                trip_id=trip.id,
                notification_type=NotificationType.TRIP_CREATED,
                title="New Trip",
                body=f"{creator_name} started a new trip: {trip.title}",
            )
        except NotificationError as e:
            db.rollback()
            logger.error(f"Failed to send trip notification (FCM error): {e.detail}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to send trip notification: {str(e)}", exc_info=True)

    return trip


def delete_trip(
    db: Session,
    trip_id: int,
    actor_id: int,
) -> tuple[str, datetime]:
    try:
        with db.begin():
            trip = db.query(Trip).filter(Trip.id == trip_id).first()

            if not trip or not can_modify_trip(trip, actor_id):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Trip not found",
                )

            trip_title = trip.title
            trip_created_at = trip.created_at

            stop_ids = [
                stop_id
                for (stop_id,) in db.query(Stop.id).filter(
                    Stop.trip_id == trip_id
                ).all()
            ]

            if stop_ids:
                db.query(Post).filter(
                    Post.stop_id.in_(stop_ids)
                ).delete(synchronize_session=False)

            db.query(Stop).filter(
                Stop.trip_id == trip_id
            ).delete(synchronize_session=False)

            db.query(PrivacySettings).filter(
                PrivacySettings.entity_type == PrivacyEntityType.trip,
                PrivacySettings.entity_id == trip_id,
            ).delete(synchronize_session=False)

            db.query(Trip).filter(
                Trip.id == trip_id
            ).delete(synchronize_session=False)

    except HTTPException:
        raise
    except Exception as e:
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete trip",
        )

    return trip_title, trip_created_at


def filter_visible_trips(
    db: Session,
    trips: list[Trip],
    viewer_id: int,
) -> list[Trip]:
    privacy_by_trip, friend_ids = load_trip_visibility_data(
        db,
        trips,
        viewer_id,
    )
    return [
        trip
        for trip in trips
        if can_view_trip(
            db,
            trip,
            viewer_id,
            friend_ids=friend_ids,
            privacy_by_trip=privacy_by_trip,
        )
    ]
