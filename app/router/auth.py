from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from app.schema.account import ConfirmAccount, ConfirmAccountOut
from app import models, enums 
from app.utils import  oauth2
from sqlalchemy.orm import Session

from app.utils.error_handling import exception_handler
from ..database import get_db
from app.services.confirmation_code import confirme_account , disable_code
from app.schema.auth import Token, TokenData 
from app.schema.user import UserOut 
from datetime import datetime
from app.utils import oauth2
from fastapi.security import OAuth2PasswordRequestForm
from app.utils import general_util
from app.config import settings
from fastapi import Response
router = APIRouter()


def _use_secure_cookies() -> bool:
    return settings.environment.strip().lower() in {"production", "prod"}


@router.patch('/confirmAccount', response_model= ConfirmAccountOut)
def confirm_account(entry: ConfirmAccount, db: Session = Depends(get_db)): 
    confirmation_code = db.query(models.ConfirmationCode).filter(models.ConfirmationCode.code == entry.confirmation_code).first() 
    if not confirmation_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid confirmation code")
    if confirmation_code.expires_at is not None and confirmation_code.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code has expired",
        )
    if confirmation_code.status != enums.CodeStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code has already been used",
        )
    if confirmation_code.user_id != entry.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation code does not match user",
        )
    try:
        confirme_account(confirmation_code.email, db)
        disable_code(confirmation_code.code, db)
        db.commit()
    except Exception as e:
        db.rollback()
        exception_handler(e, db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="There is a problem, try again",
        )

    return ConfirmAccountOut(
        message="Account Confirmed",
        status_code=status.HTTP_200_OK
    )

@router.post('/login', response_model= UserOut)
def login_user(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db) , response: Response  = None):
    user = db.query(models.User).filter(
                models.User.email == user_credentials.username).first()

    if not user:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    if  user.is_confirmed.value != enums.ConfirmedEnum.Confirmed.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email has not been verified yet",
        )
    if not general_util.verify_password(user_credentials.password, user.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid Credentials")
    data = {
        "user": {
            "full_name": user.firstname + " " + user.lastname,
            "id": user.id,
            "email": user.email     
        }
     }
    access_token = oauth2.create_access_token(data=data)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_use_secure_cookies(),
        samesite="strict",
        max_age=10000 * 60,
        path="/"
    )
    return UserOut(**user.__dict__,
    message="Login successful",
    access_token=access_token,
    status_code=status.HTTP_200_OK
        )

    
@router.post('/logout')
def logout_user(current_user: TokenData = Depends(oauth2.get_current_user), response: Response  = None):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=_use_secure_cookies(),
        samesite="strict",
        path="/"
    )
    return Token(
        message="Logout successful",
        status_code=status.HTTP_200_OK
    )
@router.get("/auth/verify")
def verify_session(current_user: TokenData = Depends(oauth2.get_current_user)):
    return { "valid": True }
