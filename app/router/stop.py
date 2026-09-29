from fastapi import APIRouter , status , BackgroundTasks
from fastapi.params import Depends
from app import enums
from sqlmodel import Session
from Dbengin import get_db
from app import models
from app.models import Stop , Trip , City
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
        return StopBaseOut(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Trip not found"
        )

    try:
        # Validate stop insertion position
        # order 0 = departure
        # last order = destination
        # New stops can only be inserted between them
        stop_count = (
            db.query(Stop)
            .filter(Stop.trip_id == trip_id)
            .count()
        )

        if entry.order < 1 or entry.order >= stop_count:
            return StopBaseOut(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Stops can only be added between departure and destination"
            )

        # Find existing city or create a new one
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

        # Shift existing stops to make room
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

    except Exception as e:
        db.rollback()
        exception_handler(e, db)

        return StopBaseOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to add stop"
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
        return StopsOut(status_code=status.HTTP_404_NOT_FOUND, message="Trip not found")
    if not can_view_trip(db, trip, current_user.user_id):
        return StopsOut(status_code=status.HTTP_403_FORBIDDEN, message="You do not have permission to view this trip")

    stops = db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.order).all()
    stops_out = [StopOut.model_validate(stop) for stop in stops]

    return StopsOut(
        stops=stops_out,
        status_code=status.HTTP_200_OK,
        message="Stops retrieved successfully"
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
        return OurBaseOut(
            status_code=status.HTTP_404_NOT_FOUND,
            message="Trip not found"
        )

    try:
        stops = (
            db.query(Stop)
            .filter(Stop.trip_id == trip_id)
            .order_by(Stop.order)
            .all()
        )

        if len(stops) < 2:
            return OurBaseOut(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="A trip must have at least departure and destination stops"
            )

        if len(entry.stop_ids) != len(set(entry.stop_ids)):
            return OurBaseOut(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Duplicate stop ids are not allowed"
            )

        existing_stop_ids = {
            stop.id for stop in stops
        }

        if set(entry.stop_ids) != existing_stop_ids:
            return OurBaseOut(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="stop_ids must contain all stops for this trip exactly once"
            )

        departure_stop_id = stops[0].id
        destination_stop_id = stops[-1].id

        if entry.stop_ids[0] != departure_stop_id:
            return OurBaseOut(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Departure stop cannot be moved"
            )

        if entry.stop_ids[-1] != destination_stop_id:
            return OurBaseOut(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="Destination stop cannot be moved"
            )
        stops_by_id = {
            stop.id: stop
            for stop in stops
        }

        # Move all stops to temporary negative positions to avoid UniqueConstraint conflicts
        for index, stop_id in enumerate(entry.stop_ids):
            stop = stops_by_id[stop_id]
            stop.order = -(index + 1)

        db.flush()

        # Apply final order
        for index, stop_id in enumerate(entry.stop_ids):
            stop = stops_by_id[stop_id]
            stop.order = index

        db.commit()

    except Exception as e:
        db.rollback()
        exception_handler(e, db)

        return OurBaseOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Failed to reorder stops"
        )

    return OurBaseOut(
        status_code=status.HTTP_200_OK,
        message="Stops reordered successfully"
    )