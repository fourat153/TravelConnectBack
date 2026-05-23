from fastapi import APIRouter, Depends, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from ..database import get_db
from app.models.post import Post
from app.models.image import Image
from app.models.stop import Stop
from app.schema.post import PostsOut, SinglePostOut, PostOut
from app.utils.cloudinary import upload_image
from app.utils.error_handling import exception_handler
from app.utils import oauth2

router = APIRouter()


@router.get('/stops/{stop_id}/posts', response_model=PostsOut, status_code=status.HTTP_200_OK)
def get_stop_posts(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    stop = db.query(Stop).filter(Stop.id == stop_id).first()
    if not stop:
        return PostsOut(status_code=status.HTTP_404_NOT_FOUND, message="Stop not found")

    posts = db.query(Post).filter(Post.stop_id == stop_id).all()
    return PostsOut(
        status_code=status.HTTP_200_OK,
        message="Posts retrieved successfully",
        posts=[PostOut.model_validate(p) for p in posts]
    )


@router.post('/stops/{stop_id}/posts', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
def create_post(
    stop_id: int,
    title: str = Form(...),
    images: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    try:
        stop = db.query(Stop).filter(Stop.id == stop_id).first()
        if not stop:
            return SinglePostOut(status_code=status.HTTP_404_NOT_FOUND, message="Stop not found")

        post = Post(stop_id=stop_id, title=title)
        db.add(post)
        db.flush()

        for file in images:
            url = upload_image(file.file.read())
            image = Image(post_id=post.id, link=url)
            db.add(image)

        db.commit()
        db.refresh(post)

    except Exception as e:
        db.rollback()
        error = exception_handler(e, db)
        return SinglePostOut(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=error,
        )

    return SinglePostOut(
        status_code=status.HTTP_201_CREATED,
        message="Post created successfully",
        post=PostOut.model_validate(post)
    )