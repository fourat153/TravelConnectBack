import uuid
from fastapi import APIRouter , status
from fastapi.params import Depends
from app import enums
from sqlmodel import Session
from app.schema.confirmation_code import ConfirmationCodeCreate
from Dbengin import get_db
from app import models
from app.schema.user import UserCreate, UserOut
from app.utils.emailUtils import send_email
from app.utils.general_util import hash_password
from app.utils.error_handling import exception_handler
from app.services.user import get_user
from app.utils import oauth2
from app.enums import PrivacyEntityType, Onboarding
from app.schema.onboarding import OnboardingData  , OnboardingOut




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
        code=str(uuid.uuid1()),
        status= enums.CodeStatus.pending,
        expires_at="2024-12-31 23:59:59"
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
        return UserOut(
            message="User with this email already exists",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if entry.password != entry.confirm_password:
        return UserOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message="Passwords must match!"
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
    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return UserOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
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


@router.delete("/users/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(user_id: int, db: Session = Depends(get_db)):
    return delete_user_from_db(user_id,db)

@router.put("/users/{user_id}", response_model=UserOut, status_code=status.HTTP_200_OK)
def update_user(user_id: int, entry: UserCreate, db: Session = Depends(get_db)):
    return update_user_in_db(user_id, entry, db)



@router.post("/users/me/onboarding" , response_model=OnboardingOut ,status_code=status.HTTP_200_OK)
def complete_onboarding(
    data: OnboardingData,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    user = db.query(models.User).filter(models.User.id == current_user.user_id).first()

    home_city = models.City(
    lat = data.lat,
    long = data.lon
    )
    db.add(home_city)
    db.flush()
    user.city_id = home_city.id 
    user.has_completed_onboarding = Onboarding.Onboarded

    privacy_setting = models.PrivacySettings(
        entity_type=PrivacyEntityType.user,
        entity_id=user.id,
        privacy_type= data.privacy,
    )
    db.add(privacy_setting)
    db.flush()
    db.commit()
    db.refresh(user)

    return OnboardingOut(
 
        has_completed_onboarding = Onboarding.Onboarded,
        status_code=status.HTTP_201_CREATED,
        message="Onboarding completed successfully"
    )
