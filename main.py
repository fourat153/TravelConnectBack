from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from app import router
from app import models

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router.user.router)
app.include_router(router.auth.router)
app.include_router(router.trip.router)
app.include_router(router.city.router)
app.include_router(router.stop.router)
app.include_router(router.privacy_settings.router)
app.include_router(router.post.router)
app.include_router(router.friendships.router)

@app.get("/")
async def root():
    return {"message": "Hello World"}