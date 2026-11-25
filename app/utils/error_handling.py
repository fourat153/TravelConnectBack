def exception_handler(e, db , error_key = ""):
    from app.router.error import commit_error_in_DB

    commit_error_in_DB(e, db)

    