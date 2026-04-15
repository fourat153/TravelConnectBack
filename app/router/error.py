from app.schema.error_logger import ErrorLoggerOut
from sqlalchemy.orm import Session
from fastapi import status , Depends
from app.database import get_db
from app.models.error_logger import ErrorLogger
from app.schema.error_logger import ErrorLoggerOut

def commit_error_in_DB(e,db:Session = Depends(get_db)):
    orig = str(e.orig) if hasattr(e, "orig") else str(e)
    statment = str(e.statement) if hasattr(e, "statement") else ''
    params = str(e.params) if hasattr(e, "params") else ''
    error = ErrorLogger(
        orig=orig,
        statement=statment,
        params=params
    )
    try:
        db.add(error)
        db.commit()
        db.refresh(error)
    except Exception as e:
        db.rollback()
        return ErrorLoggerOut(
            message="somthing went wrong",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    return ErrorLoggerOut(
        message="error added to DB successfully",
        status_code=status.HTTP_201_CREATED
    )


    