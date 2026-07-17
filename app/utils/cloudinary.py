import cloudinary
import cloudinary.uploader
from app.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

def upload_image(file_bytes: bytes, folder: str = "posts") -> str:
    result = cloudinary.uploader.upload(file_bytes, folder=folder)
    return result["secure_url"]


def upload_video(file_bytes: bytes, folder: str = "posts") -> str:
    result = cloudinary.uploader.upload_large(file_bytes, folder=folder, resource_type="video")
    return result["secure_url"]