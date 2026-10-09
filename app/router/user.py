import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, status, File, Form, UploadFile
from fastapi.params import Depends
from .. import enums
from sqlmodel import Session
from ..schema.confirmation_code import ConfirmationCodeCreate
from Dbengin import get_db
from .. import models
from ..schema.user import UserCreate, UserOut
from ..utils.emailUtils import send_email
from ..utils.general_util import hash_password
from ..utils.error_handling import exception_handler
from ..services.user import get_user
from ..utils import oauth2
from ..enums import PrivacyEntityType, Onboarding
from ..schema.onboarding import OnboardingData, OnboardingOut
from app.utils.cloudinary import upload_image
from app.schema.city import CityOut, CityData
from app.enums.gender_enum import GenderEnum

router = APIRouter()


def add_confirmation_code(confirmation_code: ConfirmationCodeCreate, db: Session = Depends(get_db)):
    confirmation_code = models.ConfirmationCode(**confirmation_code.dict())
    db.add(confirmation_code)
    db.flush()
    return confirmation_code

async def sendConfirmationMail(email:str, user_id:int, db : Session):
    confirmation_code = ConfirmationCodeCreate(
        user_id=user_id,
        email=email,
        code=secrets.token_urlsafe(32),
        status= enums.CodeStatus.pending,
        expires_at=datetime.utcnow() + timedelta(hours=24)
    )
    add_confirmation_code(confirmation_code, db)
    subject = "Account Confirmation"
    recipients = [email]
    await send_email(subject, recipients, enums.EmailTemplate.confirmaccount, email,confirmation_code.code , user_id)
   


@router.post("/users" , response_model=UserOut , status_code= status.HTTP_201_CREATED)
async def create_user(entry: UserCreate, db: Session = Depends(get_db)):
    user_in_db = db.query(models.User).filter(models.User.email == entry.email).first()
    if user_in_db:
      if user_in_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )
    if entry.password != entry.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords must match!",
        )

    try:
       entry.password = hash_password(entry.password)
       user = entry.dict()
       user.pop("confirm_password")
       user = models.User(**user)
       db.add(user)
       db.flush()
       await sendConfirmationMail(user.email, user.id, db)
       db.commit()
       db.refresh(user)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    return UserOut(**user.__dict__,
        status_code=status.HTTP_201_CREATED,
        message="User created successfully and a confirmation email sent."
    )

@router.get("/users/me", response_model= UserOut  , status_code=status.HTTP_200_OK)
def get_current(db: Session = Depends(get_db) , current_user=Depends(oauth2.get_current_user)):
        return get_user(current_user.user_id,db)

@router.get("/users/{user_id}", response_model=UserOut ,  status_code=status.HTTP_200_OK)
def get_user_by_id(user_id: int, db: Session = Depends(get_db) , current_user=Depends(oauth2.get_current_user) ):
        return get_user(user_id, db)


@router.post("/users/me/onboarding", response_model=OnboardingOut, status_code=status.HTTP_200_OK)
def complete_onboarding(
    data: OnboardingData,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        user = db.query(models.User).filter(models.User.id == current_user.user_id).first()
        home_city = models.City(
            lat=data.lat,
            long=data.lon
        )
        db.add(home_city)
        db.flush()
        user.city_id = home_city.id
        user.has_completed_onboarding = Onboarding.Onboarded
        privacy_setting = models.PrivacySettings(
            entity_type=PrivacyEntityType.user,
            entity_id=user.id,
            privacy_type=data.privacy,
        )
        db.add(privacy_setting)
        db.flush()
        db.commit()
        db.refresh(user)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete onboarding",
        )
    return OnboardingOut(
        has_completed_onboarding=Onboarding.Onboarded,
        status_code=status.HTTP_200_OK,
        message="Onboarding completed successfully"
    )

@router.get("/users/me/city", response_model=CityOut, status_code=status.HTTP_200_OK)
def get_current_user_city(
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    user = db.query(models.User).filter(models.User.id == current_user.user_id).first()
    if not user or not user.city_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found for user")
    city = db.query(models.City).filter(models.City.id == user.city_id).first()
    if not city:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="City not found")
    return CityOut(
        status_code=status.HTTP_200_OK,
        message="City retrieved successfully",
        lat=city.lat,
        long=city.long
    )

@router.put("/users/me", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_user_profile(
    firstname: str = Form(...),
    lastname: str = Form(...),
    email: str = Form(...),
    gender: Optional[GenderEnum] = Form(None),
    phone_number: Optional[str] = Form(None),
    city_lat: Optional[float] = Form(None),
    city_lon: Optional[float] = Form(None),
    profile_picture: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        user = db.query(models.User).filter(models.User.id == current_user.user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if email != user.email:
            existing = db.query(models.User).filter(models.User.email == email).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")
            user.email = email

        user.firstname = firstname
        user.lastname = lastname
        user.gender = gender
        user.phone_number = phone_number

        if city_lat is not None and city_lon is not None:
            city = db.query(models.City).filter(models.City.lat == city_lat, models.City.long == city_lon).first()
            if not city:
                city = models.City(lat=city_lat, long=city_lon)
                db.add(city)
                db.flush()
            user.city_id = city.id

        if profile_picture and profile_picture.filename:
            url = upload_image(profile_picture.file.read(), folder="profiles")
            user.profile_picture = url

        db.commit()
        db.refresh(user)

        return UserOut(
            id=user.id,
            email=user.email,
            firstname=user.firstname,
            lastname=user.lastname,
            gender=user.gender,
            phone_number=user.phone_number,
            profile_picture=user.profile_picture,
            has_completed_onboarding=user.has_completed_onboarding,
            status_code=status.HTTP_200_OK,
            message="Profile updated successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )