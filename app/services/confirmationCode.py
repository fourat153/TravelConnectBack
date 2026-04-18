from fastapi import status
from app.schema.account import ConfirmAccountOut, ConfirmAccount
from app import models
from sqlalchemy.orm import Session
from fastapi.params import Depends
from ..database import get_db
from app.schema.user import UserConfirm
from app.enums.accountStatusEnum import AccountStatusEnum
from app.enums.confirmed import ConfirmedEnum
from app.enums.code_status import CodeStatus
from app.schema.confirmation_code import CodeDeactivate


def confirme_account(email : str , db :  Session = Depends(get_db)):
    user_query = db.query(models.User).filter(models.User.email == email)
    user = user_query.first()
    if not user:
        return ConfirmAccountOut(
            message="User with this email does not exist",
            status_code=status.HTTP_404_NOT_FOUND
        )
    update = UserConfirm(is_confirmed= ConfirmedEnum.Confirmed , status= AccountStatusEnum.active)
    user_query.update(update.dict(), synchronize_session=False)
def disable_code(confirmation_code: str, db : Session = Depends(get_db)):
    code_query = db.query(models.ConfirmationCode).filter(models.ConfirmationCode.code == confirmation_code)
    code = code_query.first()
    if not code:
        return ConfirmAccountOut(
            message="Confirmation code not found",
            status_code=status.HTTP_404_NOT_FOUND
        )
    fields_to_update = CodeDeactivate(
        status= CodeStatus.used)
    code_query.update(fields_to_update.dict(), synchronize_session=False)
