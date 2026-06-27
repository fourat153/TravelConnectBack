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
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.user_id).first()
    if not trip:
        return StopBaseOut(status_code=status.HTTP_404_NOT_FOUND, message="Trip not found")

    city = db.query(City).filter(City.lat == entry.lat, City.long == entry.long).first()
    if not city:
        city = City(lat=entry.lat, long=entry.long)
        db.add(city)
        db.flush()
    #need to add a check on the unicity of city 
    last_stop = db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.order.desc()).first()
    order = (last_stop.order + 1) if last_stop else 1
    
    try:
        stop = Stop(
            trip_id=trip_id,
            city_id=city.id,
            title=entry.title,
            description=entry.description,
            order=order
        )
        db.add(stop)
        db.commit()
        db.refresh(stop)
        db.refresh(city)
    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return StopBaseOut(status_code=status.HTTP_400_BAD_REQUEST, message="Failed to add stop")
    background_tasks.add_task(increment_city_affinity, current_user.user_id, city.id)
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

    stops = db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.order).all()
    stops_out = [StopOut.model_validate(stop) for stop in stops]

    return StopsOut(
        stops=stops_out,
        status_code=status.HTTP_200_OK,
        message="Stops retrieved successfully"
    )

@router.put('/trips/{trip_id}/stops/reorder', response_model=OurBaseOut, status_code=status.HTTP_200_OK)
def reorder_stops(
    trip_id: int,
    entry: StopReorder,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.user_id).first()
    if not trip:
        return OurBaseOut(status_code=status.HTTP_404_NOT_FOUND, message="Trip not found")

    # First pass: Set to temporary negative values to avoid UniqueConstraint conflicts
    for index, stop_id in enumerate(entry.stop_ids):
        stop = db.query(Stop).filter(Stop.id == stop_id, Stop.trip_id == trip_id).first()
        if stop:
            stop.order = -(index + 1)
            db.add(stop)
    
    try:
        db.flush()
    except Exception as e:
        db.rollback()
        return OurBaseOut(status_code=status.HTTP_400_BAD_REQUEST, message="Failed to flush temporary stop order")

    # Second pass: Set to final 0-indexed values
    for index, stop_id in enumerate(entry.stop_ids):
        stop = db.query(Stop).filter(Stop.id == stop_id, Stop.trip_id == trip_id).first()
        if stop:
            stop.order = index
            db.add(stop)
    
    try:
        db.commit()
    except Exception as e:
        db.rollback()
        return OurBaseOut(status_code=status.HTTP_400_BAD_REQUEST, message="Failed to commit final stop order")

    return OurBaseOut(status_code=status.HTTP_200_OK, message="Stops reordered successfully")