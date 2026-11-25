from typing import Annotated, List
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schema.post_interactions import (
    CommentCreate,
    CommentData,
    CommentsOut,
    LikeData,
    SingleCommentOut,
    SingleLikeOut,
)
from app.schema.post import FeedPostOut, FeedPostsOut, PostOut, PostsOut, SinglePostOut
from app.services import post as post_service
from app.utils import oauth2

router = APIRouter()


@router.get('/stops/{stop_id}/posts', response_model=PostsOut, status_code=status.HTTP_200_OK)
def get_stop_posts(
    stop_id: int,
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    return post_service.get_stop_posts(
        db,
        stop_id,
        page_number,
        page_size,
        current_user.user_id,
    )

@router.post('/stops/{stop_id}/posts', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    stop_id: int,
    title: Annotated[str, Form()],
    images: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    post = await post_service.create_post(
        db,
        stop_id,
        title,
        images,
        videos,
        current_user.user_id,
    )

    return SinglePostOut(
        status_code=status.HTTP_201_CREATED,
        message="Post created successfully",
        post=PostOut.model_validate(post)
    )

@router.delete('/posts/{post_id}', response_model=SinglePostOut, status_code=status.HTTP_200_OK)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    post_service.delete_post(db, post_id, current_user.user_id)

    return SinglePostOut(
        status_code=status.HTTP_200_OK,
        message="Post deleted successfully",
    )

@router.get('/posts/{post_id}/comments', response_model=CommentsOut, status_code=status.HTTP_200_OK)
def get_post_comments(
    post_id: int,
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    return post_service.get_post_comments(
        db,
        post_id,
        page_number,
        page_size,
        current_user.user_id,
    )

@router.post('/posts/{post_id}/comments', response_model=SingleCommentOut, status_code=status.HTTP_201_CREATED)
def create_post_comment(
    post_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    comment = post_service.create_post_comment(
        db,
        post_id,
        payload,
        current_user.user_id,
    )

    return SingleCommentOut(
        status_code=status.HTTP_201_CREATED,
        message="Comment created successfully",
        data=CommentData.model_validate(comment)
    )

@router.post('/posts/{post_id}/likes', response_model=SingleLikeOut, status_code=status.HTTP_201_CREATED)
def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    like = post_service.like_post(db, post_id, current_user.user_id)

    return SingleLikeOut(
        status_code=status.HTTP_201_CREATED,
        message="Post liked successfully",
        data=LikeData.model_validate(like)
    )

@router.delete('/posts/{post_id}/likes', response_model=SingleLikeOut, status_code=status.HTTP_200_OK)
def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    post_service.unlike_post(db, post_id, current_user.user_id)

    return SingleLikeOut(
        status_code=status.HTTP_200_OK,
        message="Post unliked successfully",
    )

@router.get('/posts/feed', response_model=FeedPostsOut, status_code=status.HTTP_200_OK)
def get_feed_posts(
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    return post_service.get_feed_posts(
        db,
        page_number,
        page_size,
        current_user.user_id,
    )

@router.get('/posts/{post_id}', response_model=FeedPostOut, status_code=status.HTTP_200_OK)
def get_post_by_id(
    post_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    return post_service.get_post_by_id(db, post_id, current_user.user_id)

@router.get('/posts/user/{user_id}', response_model=FeedPostsOut, status_code=status.HTTP_200_OK)
def get_user_posts(
    user_id: int,
    page_number: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    return post_service.get_user_posts(
        db,
        user_id,
        page_number,
        page_size,
        current_user.user_id,
    )

@router.post('/posts/feed', response_model=SinglePostOut, status_code=status.HTTP_201_CREATED)
async def create_feed_post(
    title: Annotated[str, Form()],
    location: Annotated[str, Form()],
    lat: Annotated[float, Form()] = 0.0,
    long: Annotated[float, Form()] = 0.0,
    images: List[UploadFile] = File(default=[]),
    videos: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db),
    current_user=Depends(oauth2.get_current_user)
):
    post = await post_service.create_feed_post(
        db,
        title,
        location,
        lat,
        long,
        images,
        videos,
        current_user.user_id,
    )

    return SinglePostOut(
        status_code=status.HTTP_201_CREATED,
        message="Feed post created successfully",
        post=PostOut.model_validate(post)
    )
