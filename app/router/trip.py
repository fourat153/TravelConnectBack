from fastapi import APIRouter, HTTPException , status
from fastapi.params import Depends
from app.enums import PrivacyEntityType , PrivacyType
from sqlmodel import Session
from app.utils.error_handling import exception_handler
from Dbengin import get_db
from app.models import User, City, Trip , PrivacySettings, Friendship , Stop
from app.services.user import get_user
from app.schema.trip import TripCreate, TripBaseOut , TripsOut , TripOut
from app.schema.friendships import FriendFirstStop
from app.schema.city import CityOut , CityCreate , CityData
from app.schema.stop import StopInput
from app import schema
from app.utils import oauth2
from typing import Optional

router = APIRouter()


@router.post('/trips', response_model=TripBaseOut, status_code=status.HTTP_201_CREATED)
def create_trip(
    entry: TripCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    user = db.query(User).filter(User.id == current_user.user_id).first()

    home_city = None
    if entry.include_home_city:
        city_obj = db.query(City).filter(City.id == user.city_id).first()
        if city_obj:
            home_city = CityData.model_validate(city_obj)

    user_profile_privacy = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.user,
        PrivacySettings.entity_id == user.id
    ).first()
    privacy_type = PrivacyType(entry.privacy) if entry.privacy else user_profile_privacy.privacy_type

    try:

        trip = Trip(
            user_id=current_user.user_id,
            title=entry.title,
            city_id=home_city.id if home_city else None,
        )
        db.add(trip)
        db.flush()


        trip_privacy = PrivacySettings(
            entity_type=PrivacyEntityType.trip,
            entity_id=trip.id,
            privacy_type=privacy_type,
        )
        db.add(trip_privacy)

        # Normalize input: either from_city/to_city or an explicit stops list
        if entry.from_city and entry.to_city:
            stops_to_create = [
                StopInput(label=entry.from_city.label, lat=entry.from_city.lat, lon=entry.from_city.lon, order=0),
                StopInput(label=entry.to_city.label, lat=entry.to_city.lat, lon=entry.to_city.lon, order=1),
            ]
        else:
            stops_to_create = entry.stops

        for stop_input in stops_to_create:

            city = City(
                lat=stop_input.lat,
                long=stop_input.lon,
            )
            db.add(city)
            db.flush()

            stop = Stop(
                trip_id=trip.id,
                city_id=city.id,
                title=stop_input.label,
                order=stop_input.order,
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

    return TripBaseOut(
        id=trip.id,
        title=trip.title,
        city=home_city,
        created_at=trip.created_at,
        status_code=status.HTTP_201_CREATED,
        message="Trip created successfully",
    )




@router.get('/trips/me', response_model=TripsOut, status_code=status.HTTP_200_OK)
def get_my_trips(db: Session = Depends(get_db), current_user=Depends(oauth2.get_current_user)):
    trips = db.query(Trip).filter(Trip.user_id == current_user.user_id).all()
    if not trips:
        return 
        TripBaseOut(
            status_code=status.HTTP_200_OK,
            message="No trips found",
        ) 

    my_trips = [TripOut.model_validate(trip) for trip in trips]
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
        trips=[TripOut.model_validate(trip) for trip in trips],
        status_code=status.HTTP_200_OK,
        message="Trips retrieved successfully"
    )
