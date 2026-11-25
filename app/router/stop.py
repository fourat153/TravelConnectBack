from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.params import Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Stop, Trip
from app.schema.city import CityData
from app.schema.stop import StopCreate, StopBaseOut, StopsOut, StopOut
from app.utils import oauth2
from app.services.affinity import increment_city_affinity
from app.services import stop as stop_service
from app.services.trip_privacy import can_view_trip
from app.utils.pagination import div_ceil
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
    stop, city = stop_service.add_stop(
        db,
        trip_id,
        entry,
        current_user.user_id,
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
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
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

    stops_query = db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.order)
    total_records = stops_query.count()
    stops = stops_query.offset((page_number - 1) * page_size).limit(page_size).all()
    stops_out = [StopOut.model_validate(stop) for stop in stops]

    return StopsOut(
        stops=stops_out,
        status_code=status.HTTP_200_OK,
        message="Stops retrieved successfully",
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
    )


@router.delete('/stops/{stop_id}', response_model=StopBaseOut, status_code=status.HTTP_200_OK)
def delete_stop(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    stop_trip_id, stop_title, stop_order, city_data = stop_service.delete_stop(
        db,
        stop_id,
        current_user.user_id,
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
    stop_service.reorder_stops(
        db,
        trip_id,
        entry,
        current_user.user_id,
    )

    return OurBaseOut(
        status_code=status.HTTP_200_OK,
        message="Stops reordered successfully"
    )