from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from app.schema.account import ConfirmAccount, ConfirmAccountOut
from app.schema.city import CityCreate, CityOut,CityData
from app import models, enums
from app.utils import  oauth2
from sqlalchemy.orm import Session
from ..database import get_db
from app.utils.error_handling import exception_handler


router = APIRouter()

@router.get('/cities')
def get_cities(db: Session = Depends(get_db)):
    cities = db.query(models.City).all()
    return cities

@router.post('/cities', response_model=CityOut, status_code=status.HTTP_201_CREATED)
def create_city(
    entry: CityCreate,
    db: Session = Depends(get_db)
):
    try:
        city_in_db = db.query(models.City).filter(
            models.City.lat == entry.lat,
            models.City.long == entry.long
        ).first()

        if city_in_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="City with these coordinates already exists",
            )

        new_city = models.City(**entry.model_dump())
        db.add(new_city)
        db.flush()
        db.commit()
        db.refresh(new_city)

    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create city",
        )

    return CityOut(
        status_code=status.HTTP_201_CREATED,
        message="City created successfully",
        city=CityData.model_validate(new_city)
    )
