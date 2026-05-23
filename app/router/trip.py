from fastapi import APIRouter , status
from fastapi.params import Depends
from app.enums import PrivacyEntityType , PrivacyType
from sqlmodel import Session
from app.utils.error_handling import exception_handler
from Dbengin import get_db
from app.models import User, City, Trip , PrivacySettings, Friendship
from app.services.user import get_user
from app.schema.trip import TripCreate, TripBaseOut , TripsOut , TripOut
from app.schema.city import CityOut , CityCreate , CityData
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
    if entry.include_home_city :
        city_obj = db.query(City).filter(City.id == user.city_id).first()
        if city_obj:
            home_city = CityData.model_validate(city_obj)

    user_profil_privacy = db.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.user,
        PrivacySettings.entity_id == user.id).first()
    privacy_type = PrivacyType(entry.privacy) if entry.privacy else user_profil_privacy.privacy_type

    try:
        trip = Trip(
            user_id=user.id,
            title=entry.title,
            city_id=home_city.id if home_city else None,
        )
        db.add(trip)
        db.flush() 

        trip_privacy = PrivacySettings(
            entity_type=PrivacyEntityType.trip, 
            entity_id=trip.id,                  
            privacy_type=privacy_type
        )
        db.add(trip_privacy)
        db.commit()
        db.refresh(trip)
        db.refresh(trip_privacy)
    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return TripBaseOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to create trip",
        )

    return TripBaseOut(
        id=trip.id,
        city=home_city,
        title = trip.title,
        status_code=status.HTTP_201_CREATED,
        message="Trip created successfully"
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
