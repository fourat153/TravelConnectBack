from fastapi import APIRouter , status
from fastapi.params import Depends
from app import enums
from sqlmodel import Session
from Dbengin import get_db
from app import models
from app.models import Stop , Trip , City
from app.schema.city import CityData
from app.schema.stop import StopCreate, StopBaseOut, StopsOut, StopOut
from app.utils import oauth2

router = APIRouter()

@router.post('/trips/{trip_id}/stops', response_model=StopBaseOut, status_code=status.HTTP_201_CREATED)
def add_stop(
    trip_id: int,
    entry: StopCreate,
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
        return StopBaseOut(status_code=status.HTTP_400_BAD_REQUEST, message="Failed to add stop")

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
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == current_user.user_id).first()
    if not trip:
        return StopsOut(status_code=status.HTTP_404_NOT_FOUND, message="Trip not found")

    stops = db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.order).all()
    stops_out = [StopOut.model_validate(stop) for stop in stops]

    return StopsOut(
        stops=stops_out,
        status_code=status.HTTP_200_OK,
        message="Stops retrieved successfully"
    )