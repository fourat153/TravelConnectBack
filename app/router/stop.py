from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.params import Depends
from app import enums
from sqlmodel import Session
from Dbengin import get_db
from app import models
from app.models import Stop , Trip , City, Post
from app.schema.city import CityData
from app.schema.stop import StopCreate, StopBaseOut, StopsOut, StopOut
from app.utils import oauth2
from app.utils.error_handling import exception_handler
from app.services.affinity import increment_city_affinity
from app.services.trip_privacy import can_view_trip
from app.schema.stop import StopReorder
from app.schema.our_base_model import OurBaseOut

router = APIRouter()

@router.post('/trips/{trip_id}/stops', response_model=StopBaseOut, status_code=status.HTTP_201_CREATED)
def add_stop(
    trip_id: int,
    entry: StopCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    trip = (
        db.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.user_id
        )
        .first()
    )

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    try:
       
        stop_count = (
            db.query(Stop)
            .filter(Stop.trip_id == trip_id)
            .count()
        )

        if entry.order < 1 or entry.order >= stop_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stops can only be added between departure and destination",
            )

        city = (
            db.query(City)
            .filter(
                City.lat == entry.lat,
                City.long == entry.long
            )
            .first()
        )

        if not city:
            city = City(
                lat=entry.lat,
                long=entry.long
            )
            db.add(city)
            db.flush()

        stops_to_shift = (
            db.query(Stop)
            .filter(
                Stop.trip_id == trip_id,
                Stop.order >= entry.order
            )
            .order_by(Stop.order.desc())
            .all()
        )

        for stop_to_shift in stops_to_shift:
            stop_to_shift.order += 1

        stop = Stop(
            trip_id=trip_id,
            city_id=city.id,
            title=entry.title,
            description=entry.description,
            order=entry.order
        )

        db.add(stop)

        db.commit()
        db.refresh(stop)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add stop",
        )

    background_tasks.add_task(
        increment_city_affinity,
        current_user.user_id,
        city.id
    )

    return StopBaseOut(
        id=stop.id,
        trip_id=stop.trip_id,
        title=stop.title,
        order=stop.order,
        city=CityData.model_validate(city),
        status_code=status.HTTP_201_CREATED,
        message="Stop added successfully"
    )


@router.get('/trips/{trip_id}/stops', response_model=StopsOut, status_code=status.HTTP_200_OK)
def get_trip_stops(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    trip = db.query(Trip).filter(Trip.id == trip_id).first()
    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    if not can_view_trip(db, trip, current_user.user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this trip",
        )

    stops = db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.order).all()
    stops_out = [StopOut.model_validate(stop) for stop in stops]

    return StopsOut(
        stops=stops_out,
        status_code=status.HTTP_200_OK,
        message="Stops retrieved successfully"
    )


@router.delete('/stops/{stop_id}', response_model=StopBaseOut, status_code=status.HTTP_200_OK)
def delete_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        with db.begin():
            stop = db.query(Stop).filter(Stop.id == stop_id).first()

            if not stop:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")

            if not stop.trip or stop.trip.user_id != current_user.user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the trip owner can delete this stop",
                )

            stop_trip_id = stop.trip_id
            stop_title = stop.title
            stop_order = stop.order
            stop_city = stop.city
            city_data = CityData.model_validate(stop_city) if stop_city else None

            db.query(Post).filter(Post.stop_id == stop_id).delete(synchronize_session=False)
            db.query(Stop).filter(Stop.id == stop_id).delete(synchronize_session=False)

    except HTTPException:
        raise
    except Exception as e:
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete stop",
        )

    return StopBaseOut(
        id=stop_id,
        trip_id=stop_trip_id,
        title=stop_title,
        order=stop_order,
        city=city_data,
        status_code=status.HTTP_200_OK,
        message="Stop deleted successfully",
    )


@router.put(
    '/trips/{trip_id}/stops/reorder',response_model=OurBaseOut,status_code=status.HTTP_200_OK)
def reorder_stops(
    trip_id: int,
    entry: StopReorder,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    trip = (
        db.query(Trip)
        .filter(
            Trip.id == trip_id,
            Trip.user_id == current_user.user_id
        )
        .first()
    )

    if not trip:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")

    try:
        stops = (
            db.query(Stop)
            .filter(Stop.trip_id == trip_id)
            .order_by(Stop.order)
            .all()
        )

        if len(stops) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A trip must have at least departure and destination stops",
            )

        if len(entry.stop_ids) != len(set(entry.stop_ids)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Duplicate stop ids are not allowed")

        existing_stop_ids = {
            stop.id for stop in stops
        }

        if set(entry.stop_ids) != existing_stop_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stop_ids must contain all stops for this trip exactly once",
            )

        departure_stop_id = stops[0].id
        destination_stop_id = stops[-1].id

        if entry.stop_ids[0] != departure_stop_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Departure stop cannot be moved")

        if entry.stop_ids[-1] != destination_stop_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Destination stop cannot be moved")
        stops_by_id = {
            stop.id: stop
            for stop in stops
        }

        # Move all stops to temporary negative positions to avoid UniqueConstraint conflicts
        for index, stop_id in enumerate(entry.stop_ids):
            stop = stops_by_id[stop_id]
            stop.order = -(index + 1)

        db.flush()

        for index, stop_id in enumerate(entry.stop_ids):
            stop = stops_by_id[stop_id]
            stop.order = index

        db.commit()

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reorder stops",
        )

    return OurBaseOut(
        status_code=status.HTTP_200_OK,
        message="Stops reordered successfully"
    )