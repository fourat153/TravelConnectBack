from fastapi import APIRouter, HTTPException, Query, status
from fastapi.params import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Trip, Friendship, Stop
from app.services.user import get_user
from app.services import trip as trip_service
from app.services.trip_privacy import (
    can_view_trip,
)
from app.schema.trip import TripCreate, TripBaseOut , TripsOut
from app.schema.friendships import FriendFirstStop
from app.utils import oauth2
from app.utils.pagination import div_ceil
router = APIRouter()
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
    trip = trip_service.create_trip(db, entry, current_user.user_id)

    return TripBaseOut(
        id=trip.id,
        title=trip.title,
        created_at=trip.created_at,
        status_code=status.HTTP_201_CREATED,
        message="Trip created successfully",
    )



@router.get('/trips/me', response_model=TripsOut, status_code=status.HTTP_200_OK)
def get_my_trips(
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user),
):
    trips_query = db.query(Trip).filter(Trip.user_id == current_user.user_id)
    total_records = trips_query.count()
    trips = trips_query.offset((page_number - 1) * page_size).limit(page_size).all()
    if not trips:
        return TripsOut(
            trips=[],
            status_code=status.HTTP_200_OK,
            message="No trips found",
            page_number=page_number,
            page_size=page_size,
            total_pages=div_ceil(total_records, page_size),
            total_records=total_records,
        )

    my_trips = [TripBaseOut.model_validate(trip) for trip in trips]
    return TripsOut(
        trips=my_trips,
        status_code=status.HTTP_200_OK,
        message="Trips retrieved successfully",
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )

@router.get('/trips/friend/{friend_id}/first-stop', response_model=FriendFirstStop, status_code=status.HTTP_200_OK)
def get_friend_first_stop(
    friend_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    is_friend = db.query(Friendship).filter(
        (
            (Friendship.user_1_id == current_user.user_id) & (Friendship.user_2_id == friend_id)
        ) | (
            (Friendship.user_2_id == current_user.user_id) & (Friendship.user_1_id == friend_id)
        )
    ).first()
    if not is_friend:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not friends with this user.",
        )

    first_trip = (
        db.query(Trip)
        .filter(Trip.user_id == friend_id)
        .order_by(Trip.id.asc())
        .first()
    )
    if not first_trip:
        raise HTTPException(status_code=404, detail="Friend has no trips")
    if not can_view_trip(db, first_trip, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )
 
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
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not friends with this user.",
        )

    trips = db.query(Trip).filter(
        Trip.user_id == user_id,
    ).all()
    visible_trips = trip_service.filter_visible_trips(
        db,
        trips,
        current_user.user_id,
    )
    total_records = len(visible_trips)
    visible_trips = visible_trips[
        (page_number - 1) * page_size:page_number * page_size
    ]

    if not trips:
        return TripsOut(
            status_code=status.HTTP_200_OK,
            message="No public trips found.",
            trips=[],
            page_number=page_number,
            page_size=page_size,
            total_pages=div_ceil(total_records, page_size),
            total_records=total_records,
        )

    return TripsOut(
        trips=[TripBaseOut.model_validate(trip) for trip in visible_trips],
        status_code=status.HTTP_200_OK,
        message="Trips retrieved successfully",
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )


@router.delete('/trips/{trip_id}', response_model=TripBaseOut, status_code=status.HTTP_200_OK)
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    trip_title, trip_created_at = trip_service.delete_trip(
        db,
        trip_id,
        current_user.user_id,
    )

    return TripBaseOut(
        id=trip_id,
        title=trip_title,
        created_at=trip_created_at,
        status_code=status.HTTP_200_OK,
        message="Trip deleted successfully"
    )
