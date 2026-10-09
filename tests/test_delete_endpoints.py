"""Integration tests for the trip / stop / post delete endpoints.

These exercise the real FastAPI app against the Postgres test database that
``conftest.py`` points the application at. Authentication is tested with real
JWTs so the actual ``get_current_user`` dependency is used.
"""
import app.models  # noqa: F401  (ensures every table is registered)
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import City, Image, Post, Stop, Trip, User, Video
from app.utils.oauth2 import create_access_token
from Dbengin import Base, SessionLocal, engine


@pytest.fixture(scope="module", autouse=True)
def _schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def _auth_header(user_id: int):
    token = create_access_token({"user": {"id": user_id}})
    return {"Authorization": f"Bearer {token}"}


def _create_user(db, email, firstname="Test", lastname="User"):
    user = User(email=email, password="secret", firstname=firstname, lastname=lastname)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user.id


def _seed_trip(db, owner_id):
    """Create one trip with two stops, a post on each stop and media on stop1's post."""
    city1 = City(lat=11.0, long=11.0)
    city2 = City(lat=22.0, long=22.0)
    db.add_all([city1, city2])
    db.commit()

    trip = Trip(user_id=owner_id, title="Owner Trip")
    db.add(trip)
    db.commit()
    db.refresh(trip)

    stop1 = Stop(trip_id=trip.id, city_id=city1.id, title="Stop 1", order=0)
    stop2 = Stop(trip_id=trip.id, city_id=city2.id, title="Stop 2", order=1)
    db.add_all([stop1, stop2])
    db.commit()
    db.refresh(stop1)
    db.refresh(stop2)

    post1 = Post(stop_id=stop1.id, user_id=owner_id, title="Post 1")
    post2 = Post(stop_id=stop2.id, user_id=owner_id, title="Post 2")
    db.add_all([post1, post2])
    db.commit()
    db.refresh(post1)
    db.refresh(post2)

    image = Image(post_id=post1.id, link="https://cdn.example/img.jpg")
    video = Video(post_id=post1.id, link="https://cdn.example/vid.mp4")
    db.add_all([image, video])
    db.commit()

    return {
        "trip": trip.id,
        "stop1": stop1.id,
        "stop2": stop2.id,
        "post1": post1.id,
        "post2": post2.id,
    }


def _counts(db):
    return {
        "trips": db.query(Trip).count(),
        "stops": db.query(Stop).count(),
        "posts": db.query(Post).count(),
        "images": db.query(Image).count(),
        "videos": db.query(Video).count(),
    }


def test_delete_endpoints_require_authentication(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.auth@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    for url in (f"/trips/{ids['trip']}", f"/stops/{ids['stop1']}", f"/posts/{ids['post1']}"):
        response = client.delete(url)
        assert response.status_code == 401, (url, response.status_code, response.text)


def test_cannot_delete_another_users_trip(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.trip@test.com")
        intruder = _create_user(db, "intruder.trip@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    response = client.delete(f"/trips/{ids['trip']}", headers=_auth_header(intruder))
    assert response.status_code == 404, response.text

    db = SessionLocal()
    try:
        assert db.query(Trip).filter(Trip.id == ids["trip"]).first() is not None
        assert db.query(Stop).filter(Stop.trip_id == ids["trip"]).count() == 2
        assert db.query(Post).filter(Post.stop_id.in_([ids["stop1"], ids["stop2"]])).count() == 2
    finally:
        db.close()


def test_cannot_delete_another_users_stop(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.stop@test.com")
        intruder = _create_user(db, "intruder.stop@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    response = client.delete(f"/stops/{ids['stop1']}", headers=_auth_header(intruder))
    assert response.status_code == 403, response.text

    db = SessionLocal()
    try:
        assert db.query(Stop).filter(Stop.id == ids["stop1"]).first() is not None
        assert db.query(Post).filter(Post.id == ids["post1"]).first() is not None
    finally:
        db.close()


def test_cannot_delete_another_users_post(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.post@test.com")
        intruder = _create_user(db, "intruder.post@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    response = client.delete(f"/posts/{ids['post1']}", headers=_auth_header(intruder))
    assert response.status_code == 403, response.text

    db = SessionLocal()
    try:
        assert db.query(Post).filter(Post.id == ids["post1"]).first() is not None
        assert db.query(Image).filter(Image.post_id == ids["post1"]).count() == 1
        assert db.query(Video).filter(Video.post_id == ids["post1"]).count() == 1
    finally:
        db.close()


def test_owner_delete_trip_cascades_stops_posts_and_media(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.delete.trip@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    response = client.delete(f"/trips/{ids['trip']}", headers=_auth_header(owner))
    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        assert db.query(Trip).filter(Trip.id == ids["trip"]).first() is None
        assert db.query(Stop).filter(Stop.trip_id == ids["trip"]).count() == 0
        assert db.query(Post).filter(Post.stop_id.in_([ids["stop1"], ids["stop2"]])).count() == 0
        assert db.query(Image).filter(Image.post_id == ids["post1"]).count() == 0
        assert db.query(Video).filter(Video.post_id == ids["post1"]).count() == 0
    finally:
        db.close()


def test_owner_delete_stop_cascades_posts_but_keeps_rest(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.delete.stop@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    response = client.delete(f"/stops/{ids['stop1']}", headers=_auth_header(owner))
    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        assert db.query(Stop).filter(Stop.id == ids["stop1"]).first() is None
        assert db.query(Post).filter(Post.stop_id == ids["stop1"]).count() == 0
        assert db.query(Image).filter(Image.post_id == ids["post1"]).count() == 0
        assert db.query(Video).filter(Video.post_id == ids["post1"]).count() == 0
        # parent trip and sibling stop/post untouched
        assert db.query(Trip).filter(Trip.id == ids["trip"]).first() is not None
        assert db.query(Stop).filter(Stop.id == ids["stop2"]).first() is not None
        assert db.query(Post).filter(Post.id == ids["post2"]).first() is not None
    finally:
        db.close()


def test_owner_delete_post_removes_media(client):
    db = SessionLocal()
    try:
        owner = _create_user(db, "owner.delete.post@test.com")
        ids = _seed_trip(db, owner)
    finally:
        db.close()

    response = client.delete(f"/posts/{ids['post1']}", headers=_auth_header(owner))
    assert response.status_code == 200, response.text

    db = SessionLocal()
    try:
        assert db.query(Post).filter(Post.id == ids["post1"]).first() is None
        assert db.query(Image).filter(Image.post_id == ids["post1"]).count() == 0
        assert db.query(Video).filter(Video.post_id == ids["post1"]).count() == 0
        # sibling post stays
        assert db.query(Post).filter(Post.id == ids["post2"]).first() is not None
    finally:
        db.close()
