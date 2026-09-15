import logging
from fastapi import APIRouter, HTTPException , status
from fastapi.params import Depends
from app.enums import NotificationType, PrivacyEntityType , PrivacyType
from sqlmodel import Session
from app.utils.error_handling import exception_handler
from Dbengin import get_db
from app.models import User, City, Trip , PrivacySettings, Friendship , Stop
from app.services.user import get_user
from app.services.notification import NotificationError
from app.services.notification_service import create_and_send_notification
from app.schema.trip import TripCreate, TripBaseOut , TripsOut
from app.schema.friendships import FriendFirstStop
from app.utils import oauth2
router = APIRouter()
logger = logging.getLogger(__name__)
"""
Every trip always contains at least two stops.
The first stop (order = 0) is the departure city,
and the last stop is the destination city. 
Additional stops may only be inserted between these two stops.

"""
@router.post('/trips', response_model=TripBaseOut, status_code=status.HTTP_201_CREATED)
def create_trip(
    entry: TripCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    user = db.query(User).filter(User.id == current_user.user_id).first()

    user_profile_privacy = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.user,
        PrivacySettings.entity_id == user.id
    ).first()
    privacy_type = PrivacyType(entry.privacy) if entry.privacy else user_profile_privacy.privacy_type

    try:

        trip = Trip(
            user_id=current_user.user_id,
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
        return TripBaseOut(
            id=0,
            title='',
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to create trip",
        )

    friends = db.query(Friendship).filter(
        (Friendship.user_1_id == current_user.user_id)
        | (Friendship.user_2_id == current_user.user_id)
    ).all()
    friend_ids = {
        friendship.user_2_id
        if friendship.user_1_id == current_user.user_id
        else friendship.user_1_id
        for friendship in friends
    }
    creator_name = f"{user.firstname} {user.lastname}"
    for friend_id in friend_ids:
        try:
            create_and_send_notification(
                db=db,
                recipient_id=friend_id,
                actor_id=current_user.user_id,
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

    return TripBaseOut(
        id=trip.id,
        title=trip.title,
        created_at=trip.created_at,
        status_code=status.HTTP_201_CREATED,
        message="Trip created successfully",
    )



@router.get('/trips/me', response_model=TripsOut, status_code=status.HTTP_200_OK)
def get_my_trips(db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    trips = db.query(Trip).filter(Trip.user_id == current_user.user_id).all()
    if not trips:
        return TripsOut(
            trips=[],
            status_code=status.HTTP_200_OK,
            message="No trips found",
        )

    my_trips = [TripBaseOut.model_validate(trip) for trip in trips]
    return TripsOut(
        trips=my_trips,
        status_code=status.HTTP_200_OK,
        message="Trips retrieved successfully"
    )

@router.get('/trips/friend/{friend_id}/first-stop', response_model=FriendFirstStop, status_code=status.HTTP_200_OK)
def get_friend_first_stop(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    first_trip = (
        db.query(Trip)
        .filter(Trip.user_id == friend_id)
        .order_by(Trip.id.asc())
        .first()
    )
    if not first_trip:
        raise HTTPException(status_code=404, detail="Friend has no trips")
 
    first_stop = (
        db.query(Stop)
        .filter(Stop.trip_id == first_trip.id)
        .order_by(Stop.order.asc())
        .first()
    )
    if not first_stop:
        raise HTTPException(status_code=404, detail="Friend's trip has no stops")
 
    return FriendFirstStop(
        lat=first_stop.city.lat,
        lon=first_stop.city.long,
        stop_title=first_stop.title,
    )

@router.get('/trips/friend/{user_id}', response_model=TripsOut, status_code=status.HTTP_200_OK)
def get_user_trips(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    is_friend = db.query(Friendship).filter(
        (
            (Friendship.user_1_id == current_user.user_id) & (Friendship.user_2_id == user_id)
        ) | (
            (Friendship.user_2_id == current_user.user_id) & (Friendship.user_1_id == user_id)
        )
    ).first()

    if not is_friend:
        return TripsOut(
            status_code=status.HTTP_403_FORBIDDEN,
            message="You are not friends with this user.",
            trips=[]
        )

    trips = db.query(Trip).filter(
        Trip.user_id == user_id,
    ).all()

    if not trips:
        return TripsOut(
            status_code=status.HTTP_200_OK,
            message="No public trips found.",
            trips=[]
        )

    return TripsOut(
        trips=[TripBaseOut.model_validate(trip) for trip in trips],
        status_code=status.HTTP_200_OK,
        message="Trips retrieved successfully"
    )


@router.delete('/trips/{trip_id}', response_model=TripBaseOut, status_code=status.HTTP_200_OK)
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        trip = db.query(Trip).filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.user_id
        ).first()

        if not trip:
            return TripBaseOut(
                id=0,
                title='',
                status_code=status.HTTP_404_NOT_FOUND,
                message="Trip not found"
            )

        # Delete privacy settings for the trip
        db.query(PrivacySettings).filter(
            PrivacySettings.entity_type == PrivacyEntityType.trip,
            PrivacySettings.entity_id == trip_id
        ).delete()

        # Delete the trip (stops will be deleted via cascade)
        db.delete(trip)
        db.commit()

    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        return TripBaseOut(
            id=0,
            title='',
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to delete trip"
        )

    return TripBaseOut(
        id=trip_id,
        title=trip.title,
        created_at=trip.created_at,
        status_code=status.HTTP_200_OK,
        message="Trip deleted successfully"
    )
