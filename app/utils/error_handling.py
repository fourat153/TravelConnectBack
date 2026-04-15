from app.router.error import commit_error_in_DB

def exception_handler(e, db , error_key = ""):
    commit_error_in_DB(e, db)

    