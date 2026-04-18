from fastapi import APIRouter , status
from fastapi.params import Depends
from app.schema.account import ConfirmAccount, ConfirmAccountOut
from app import models, enums 
from app.utils import  oauth2
from sqlalchemy.orm import Session
from ..database import get_db
from app.services.confirmationCode import confirme_account , disable_code
from app.schema.auth import Token
from datetime import datetime
from fastapi.security import OAuth2PasswordRequestForm
from app.utils import general_util
from fastapi import Response
router = APIRouter()


@router.patch('/confirmAccount', response_model= ConfirmAccountOut)
def confirm_account(entry: ConfirmAccount, db: Session = Depends(get_db)): 
    confirmation_code = db.query(models.ConfirmationCode).filter(models.ConfirmationCode.code == entry.confirmation_code).first()
    if not confirmation_code:
        return ConfirmAccountOut(
            message="Invalid confirmation code",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    '''if confirmation_code.expires_at < datetime.now():
        return ConfirmAccountOut(
            message="Confirmation code has expired",
            status_code=status.HTTP_400_BAD_REQUEST,
        )'''
    if confirmation_code.status != enums.CodeStatus.pending:
        return ConfirmAccountOut(
            message="Confirmation code has already been used",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if confirmation_code.user_id != entry.user_id:
        return ConfirmAccountOut(
            message="Confirmation code does not match user",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    try:
        confirme_account(confirmation_code.email, db)
        disable_code(confirmation_code.code, db)
        db.commit()
    except Exception as e:
        db.rollback()
        #add_error(e, db)
        return UserOut(
            message="There is a problem, try again",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return ConfirmAccountOut(
        message="Account Confirmed",
        status_code=status.HTTP_200_OK
    )

@router.post('/login', response_model= Token)
def login_user(user_credentials: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db) , response: Response  = None):
    user = db.query(models.User).filter(
                models.User.email == user_credentials.username).first()

    if not user:
        return Token(
            message="Invalid Credentials",
            status_code=status.HTTP_403_FORBIDDEN
        )
    if  user.is_confirmed.value != enums.ConfirmedEnum.Confirmed.value:
        return Token(
            message="Email has not been verified yet",
            status_code=status.HTTP_403_FORBIDDEN
        )
    if not general_util.verify_password(user_credentials.password, user.password):
        return Token(
            message="Invalid Credentials",
            status_code=status.HTTP_403_FORBIDDEN
        )
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
        httponly=False,
        secure=False,
        samesite="strict",
        max_age=15 * 60,
        path="/"
    )
    return Token(access_token=None,
                         token_type="bearer",
                         message="Login successful",
                         status_code=status.HTTP_200_OK
                )

    
router.post('/logout')
def logout_user(response: Response):
    response.delete_cookie
    return Token(
        message="Logout successful",
        status_code=status.HTTP_200_OK
    )
