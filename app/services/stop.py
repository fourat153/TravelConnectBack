from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import City, Post, Stop, Trip
from app.schema.city import CityData
from app.schema.stop import StopCreate, StopReorder
from app.services.trip_privacy import can_modify_stop, can_modify_trip
from app.utils.error_handling import exception_handler


def add_stop(
    db: Session,
    trip_id: int,
    entry: StopCreate,
    user_id: int,
) -> tuple[Stop, City]:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not trip or not can_modify_trip(trip, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

    try:
        stop_count = db.query(Stop).filter(Stop.trip_id == trip_id).count()

        if entry.order < 1 or entry.order >= stop_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Stops can only be added between departure and destination",
            )

        city = db.query(City).filter(
            City.lat == entry.lat,
            City.long == entry.long,
        ).first()

        if not city:
            city = City(lat=entry.lat, long=entry.long)
            db.add(city)
            db.flush()

        stops_to_shift = (
            db.query(Stop)
            .filter(
                Stop.trip_id == trip_id,
                Stop.order >= entry.order,
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
            order=entry.order,
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

    return stop, city


def delete_stop(
    db: Session,
    stop_id: int,
    actor_id: int,
) -> tuple[int, str | None, int, CityData | None]:
    try:
        with db.begin():
            stop = db.query(Stop).filter(Stop.id == stop_id).first()

            if not stop:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Stop not found",
                )

            if not can_modify_stop(stop, actor_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the trip owner can delete this stop",
                )

            stop_trip_id = stop.trip_id
            stop_title = stop.title
            stop_order = stop.order
            city_data = CityData.model_validate(stop.city) if stop.city else None

            db.query(Post).filter(
                Post.stop_id == stop_id
            ).delete(synchronize_session=False)
            db.query(Stop).filter(
                Stop.id == stop_id
            ).delete(synchronize_session=False)

    except HTTPException:
        raise
    except Exception as e:
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete stop",
        )

    return stop_trip_id, stop_title, stop_order, city_data


def reorder_stops(
    db: Session,
    trip_id: int,
    entry: StopReorder,
    actor_id: int,
) -> None:
    trip = db.query(Trip).filter(Trip.id == trip_id).first()

    if not trip or not can_modify_trip(trip, actor_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found",
        )

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
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate stop ids are not allowed",
            )

        existing_stop_ids = {stop.id for stop in stops}
        if set(entry.stop_ids) != existing_stop_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stop_ids must contain all stops for this trip exactly once",
            )

        departure_stop_id = stops[0].id
        destination_stop_id = stops[-1].id

        if entry.stop_ids[0] != departure_stop_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Departure stop cannot be moved",
            )

        if entry.stop_ids[-1] != destination_stop_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination stop cannot be moved",
            )

        stops_by_id = {stop.id: stop for stop in stops}

        for index, stop_id in enumerate(entry.stop_ids):
            stops_by_id[stop_id].order = -(index + 1)

        db.flush()

        for index, stop_id in enumerate(entry.stop_ids):
            stops_by_id[stop_id].order = index

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
