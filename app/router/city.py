from fastapi import APIRouter , status
from fastapi.params import Depends
from app.schema.account import ConfirmAccount, ConfirmAccountOut
from app.schema.city import CityCreate, CityOut
from app import models, enums
from app.utils import  oauth2
from sqlalchemy.orm import Session
from ..database import get_db


router = APIRouter()

@router.get('/cities')
def get_cities(db: Session = Depends(get_db)):
    cities = db.query(models.City).all()
    return cities

@router.post('/cities', status_code=status.HTTP_201_CREATED)
def create_city(entry:CityCreate , db: Session = Depends(get_db)):
    city_in_db = db.query(models.City).filter(
    models.City.lat == entry.lat,
    models.City.long == entry.long
    ).first()

    if city_in_db:
        return {
            "message": "City with this name already exists",
            "status_code": status.HTTP_400_BAD_REQUEST,
        }
    new_city = models.City(**entry.dict())
    db.add(new_city)
    db.flush()
    db.commit()
    db.refresh(new_city)
    return new_city

