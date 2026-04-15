from fastapi import FastAPI
from app import router
from app import models

app = FastAPI()
app.include_router(router.user.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}   