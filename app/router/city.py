from fastapi import APIRouter, HTTPException, Query, status
from fastapi.params import Depends
from app.schema.account import ConfirmAccount, ConfirmAccountOut
from app.schema.city import CityCreate, CityOut, CityData
from app.schema.pagination import CitiesOut
from app.utils.pagination import div_ceil
from app import models, enums
from app.utils import  oauth2
from sqlalchemy.orm import Session
from ..database import get_db
from app.utils.error_handling import exception_handler


router = APIRouter()

@router.get('/cities', response_model=CitiesOut)
def get_cities(
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    cities_query = db.query(models.City).order_by(models.City.id)
    total_records = cities_query.count()
    cities = cities_query.offset((page_number - 1) * page_size).limit(page_size).all()
    return CitiesOut(
        cities=[CityData.model_validate(city) for city in cities],
        page_number=page_number,
        page_size=page_size,
        total_pages=div_ceil(total_records, page_size),
        total_records=total_records,
        status_code=status.HTTP_200_OK,
        message="Cities retrieved successfully",
    )

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

    except HTTPException:
        raise
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
