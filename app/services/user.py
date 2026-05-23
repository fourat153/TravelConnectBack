from fastapi import status
from app.schema.user import UserOut
from app.models import User
from sqlalchemy.orm import Session
from fastapi.params import Depends
from ..database import get_db
 
def get_user(user_id : int , db : Session  = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return UserOut(
            message="User {user_id} not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return UserOut(**user.__dict__,
        message="User  retrieved successfully",
        status_code=status.HTTP_200_OK
    )
