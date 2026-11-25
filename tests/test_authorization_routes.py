from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app import models
from app.enums import FriendshipStatusEnum, PrivacyEntityType, PrivacyType
from app.main import app
from app.utils import oauth2


@pytest.fixture
def api_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    current_user = {"id": None}

    def override_get_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        return SimpleNamespace(user_id=current_user["id"])

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[oauth2.get_current_user] = override_current_user

    try:
        with TestClient(app) as client:
            yield client, test_session, current_user
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def trip_fixture(api_client):
    _, test_session, _ = api_client
    with test_session() as db:
        owner = models.User(
            email="owner@example.test",
            password="test",
            firstname="Trip",
            lastname="Owner",
        )
        friend = models.User(
            email="friend@example.test",
            password="test",
            firstname="Trip",
            lastname="Friend",
        )
        author = models.User(
            email="author@example.test",
            password="test",
            firstname="Post",
            lastname="Author",
        )
        db.add_all([owner, friend, author])
        db.flush()

        trip = models.Trip(user_id=owner.id, title="Test trip")
        departure_city = models.City(lat=10.0, long=20.0)
        destination_city = models.City(lat=30.0, long=40.0)
        db.add_all([trip, departure_city, destination_city])
        db.flush()

        departure = models.Stop(
            trip_id=trip.id,
            city_id=departure_city.id,
            title="Departure",
            order=0,
        )
        destination = models.Stop(
            trip_id=trip.id,
            city_id=destination_city.id,
            title="Destination",
            order=1,
        )
        db.add_all([departure, destination])
        db.flush()
        db.add_all(
            [
                models.PrivacySettings(
                    entity_type=PrivacyEntityType.trip,
                    entity_id=trip.id,
                    privacy_type=PrivacyType.friends_only,
                ),
                models.Friendship(user_1_id=owner.id, user_2_id=friend.id),
            ]
        )
        post = models.Post(
            stop_id=departure.id,
            user_id=author.id,
            title="A travel post",
        )
        db.add(post)
        db.commit()

        return {
            "owner_id": owner.id,
            "friend_id": friend.id,
            "author_id": author.id,
            "trip_id": trip.id,
            "departure_stop_id": departure.id,
            "destination_stop_id": destination.id,
            "post_id": post.id,
        }


def test_friend_can_view_but_cannot_modify_friends_only_trip(api_client, trip_fixture):
    client, _, current_user = api_client
    current_user["id"] = trip_fixture["friend_id"]

    read_response = client.get(
        f"/trips/{trip_fixture['trip_id']}/stops",
    )
    add_response = client.post(
        f"/trips/{trip_fixture['trip_id']}/stops",
        json={
            "lat": 50.0,
            "long": 60.0,
            "title": "Unauthorized stop",
            "order": 1,
        },
    )
    reorder_response = client.put(
        f"/trips/{trip_fixture['trip_id']}/stops/reorder",
        json={
            "stop_ids": [
                trip_fixture["departure_stop_id"],
                trip_fixture["destination_stop_id"],
            ]
        },
    )

    assert read_response.status_code == 200
    assert add_response.status_code == 404
    assert reorder_response.status_code == 404


def test_trip_owner_can_add_stop_and_destination_order_shifts(
    api_client,
    trip_fixture,
    monkeypatch,
):
    client, test_session, current_user = api_client
    current_user["id"] = trip_fixture["owner_id"]
    affinity_task = Mock()
    monkeypatch.setattr(
        "app.router.stop.increment_city_affinity",
        affinity_task,
    )

    response = client.post(
        f"/trips/{trip_fixture['trip_id']}/stops",
        json={
            "lat": 50.0,
            "long": 60.0,
            "title": "Intermediate stop",
            "description": "A short visit",
            "order": 1,
        },
    )

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["message"] == "Stop added successfully"
    affinity_task.assert_called_once_with(
        trip_fixture["owner_id"],
        response_data["city"]["id"],
    )

    with test_session() as db:
        stops = db.query(models.Stop).filter(
            models.Stop.trip_id == trip_fixture["trip_id"]
        ).order_by(models.Stop.order).all()

        assert [(stop.title, stop.order) for stop in stops] == [
            ("Departure", 0),
            ("Intermediate stop", 1),
            ("Destination", 2),
        ]


def test_non_owner_cannot_create_post_on_trip_stop(api_client, trip_fixture):
    client, _, current_user = api_client
    current_user["id"] = trip_fixture["friend_id"]

    response = client.post(
        f"/stops/{trip_fixture['departure_stop_id']}/posts",
        files={"title": (None, "Unauthorized post")},
    )

    assert response.status_code == 403


def test_trip_owner_can_create_post_with_uploaded_media(
    api_client,
    trip_fixture,
    monkeypatch,
):
    client, test_session, current_user = api_client
    current_user["id"] = trip_fixture["owner_id"]
    monkeypatch.setattr(
        "app.services.post.upload_image",
        lambda _: "https://cdn.example.test/post-image.jpg",
    )
    monkeypatch.setattr(
        "app.services.post.upload_video",
        lambda _: "https://cdn.example.test/post-video.mp4",
    )

    response = client.post(
        f"/stops/{trip_fixture['departure_stop_id']}/posts",
        data={"title": "A post with media"},
        files=[
            ("images", ("photo.jpg", b"image bytes", "image/jpeg")),
            ("videos", ("clip.mp4", b"video bytes", "video/mp4")),
        ],
    )

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["message"] == "Post created successfully"
    assert response_data["post"]["title"] == "A post with media"
    assert response_data["post"]["images"][0]["link"] == (
        "https://cdn.example.test/post-image.jpg"
    )
    assert response_data["post"]["videos"][0]["link"] == (
        "https://cdn.example.test/post-video.mp4"
    )

    with test_session() as db:
        post = db.query(models.Post).filter(
            models.Post.id == response_data["post"]["id"]
        ).one()
        assert post.stop_id == trip_fixture["departure_stop_id"]
        assert post.user_id == trip_fixture["owner_id"]


def test_friend_can_comment_and_like_visible_post(api_client, trip_fixture, monkeypatch):
    client, test_session, current_user = api_client
    current_user["id"] = trip_fixture["friend_id"]
    notification = Mock()
    notification.return_value = {"notification": SimpleNamespace(id=1)}
    monkeypatch.setattr(
        "app.services.post.create_and_send_notification",
        notification,
    )

    comment_response = client.post(
        f"/posts/{trip_fixture['post_id']}/comments",
        json={"content": "Looks like a great trip"},
    )
    like_response = client.post(
        f"/posts/{trip_fixture['post_id']}/likes",
    )
    duplicate_like_response = client.post(
        f"/posts/{trip_fixture['post_id']}/likes",
    )
    unlike_response = client.delete(
        f"/posts/{trip_fixture['post_id']}/likes",
    )

    assert comment_response.status_code == 201
    assert comment_response.json()["data"]["content"] == "Looks like a great trip"
    assert like_response.status_code == 201
    assert duplicate_like_response.status_code == 409
    assert unlike_response.status_code == 200
    notification.assert_called_once()

    with test_session() as db:
        assert db.query(models.Comment).filter(
            models.Comment.post_id == trip_fixture["post_id"]
        ).count() == 1
        assert db.query(models.PostLike).filter(
            models.PostLike.post_id == trip_fixture["post_id"],
            models.PostLike.user_id == trip_fixture["friend_id"],
        ).count() == 0


def test_create_feed_post_creates_trip_stop_post_and_media(
    api_client,
    trip_fixture,
    monkeypatch,
):
    client, test_session, current_user = api_client
    current_user["id"] = trip_fixture["author_id"]
    monkeypatch.setattr(
        "app.services.post.upload_image",
        lambda _: "https://cdn.example.test/feed-image.jpg",
    )
    monkeypatch.setattr(
        "app.services.post.upload_video",
        lambda _: "https://cdn.example.test/feed-video.mp4",
    )

    response = client.post(
        "/posts/feed",
        data={
            "title": "A feed post",
            "location": "Somewhere",
            "lat": "12.5",
            "long": "25.5",
        },
        files=[
            ("images", ("feed.jpg", b"image bytes", "image/jpeg")),
            ("videos", ("feed.mp4", b"video bytes", "video/mp4")),
        ],
    )

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["message"] == "Feed post created successfully"
    assert response_data["post"]["title"] == "A feed post"
    assert response_data["post"]["images"][0]["link"] == (
        "https://cdn.example.test/feed-image.jpg"
    )
    assert response_data["post"]["videos"][0]["link"] == (
        "https://cdn.example.test/feed-video.mp4"
    )

    with test_session() as db:
        trip = db.query(models.Trip).filter(
            models.Trip.user_id == trip_fixture["author_id"]
        ).one()
        privacy = db.query(models.PrivacySettings).filter(
            models.PrivacySettings.entity_type == PrivacyEntityType.trip,
            models.PrivacySettings.entity_id == trip.id,
        ).one()
        stop = db.query(models.Stop).filter(
            models.Stop.trip_id == trip.id
        ).one()
        post = db.query(models.Post).filter(
            models.Post.id == response_data["post"]["id"]
        ).one()

        assert trip.title == "My Travels"
        assert privacy.privacy_type == PrivacyType.public
        assert stop.title == "Somewhere"
        assert post.stop_id == stop.id


def test_post_read_workflows_enforce_trip_privacy(api_client, trip_fixture):
    client, test_session, current_user = api_client

    with test_session() as db:
        private_trip = models.Trip(
            user_id=trip_fixture["owner_id"],
            title="Private trip",
        )
        private_city = models.City(lat=130.0, long=140.0)
        db.add_all([private_trip, private_city])
        db.flush()
        private_stop = models.Stop(
            trip_id=private_trip.id,
            city_id=private_city.id,
            title="Private location",
            order=0,
        )
        db.add(private_stop)
        db.flush()
        private_post = models.Post(
            stop_id=private_stop.id,
            user_id=trip_fixture["owner_id"],
            title="Private post",
        )
        db.add_all(
            [
                models.PrivacySettings(
                    entity_type=PrivacyEntityType.trip,
                    entity_id=private_trip.id,
                    privacy_type=PrivacyType.private,
                ),
                private_post,
            ]
        )
        db.commit()
        private_post_id = private_post.id

    current_user["id"] = trip_fixture["friend_id"]
    stop_posts_response = client.get(
        f"/stops/{trip_fixture['departure_stop_id']}/posts"
    )
    comments_response = client.get(
        f"/posts/{trip_fixture['post_id']}/comments"
    )
    feed_response = client.get("/posts/feed")
    post_response = client.get(f"/posts/{trip_fixture['post_id']}")
    user_posts_response = client.get(
        f"/posts/user/{trip_fixture['owner_id']}"
    )
    private_post_response = client.get(f"/posts/{private_post_id}")

    assert stop_posts_response.status_code == 200
    assert comments_response.status_code == 200
    assert feed_response.status_code == 200
    assert post_response.status_code == 200
    assert user_posts_response.status_code == 200
    assert private_post_response.status_code == 403
    assert [
        post["id"] for post in feed_response.json()["posts"]
    ] == [trip_fixture["post_id"]]
    assert [
        post["id"] for post in user_posts_response.json()["posts"]
    ] == [trip_fixture["post_id"]]


def test_only_post_author_can_delete_post(api_client, trip_fixture):
    client, _, current_user = api_client

    current_user["id"] = trip_fixture["owner_id"]
    owner_response = client.delete(f"/posts/{trip_fixture['post_id']}")

    current_user["id"] = trip_fixture["author_id"]
    author_response = client.delete(f"/posts/{trip_fixture['post_id']}")

    assert owner_response.status_code == 403
    assert author_response.status_code == 200


def test_only_trip_owner_can_change_trip_privacy(api_client, trip_fixture):
    client, _, current_user = api_client
    current_user["id"] = trip_fixture["friend_id"]

    friend_response = client.put(
        f"/privacy-settings/trip/{trip_fixture['trip_id']}",
        json={"privacy_type": PrivacyType.private.value},
    )

    current_user["id"] = trip_fixture["owner_id"]
    owner_response = client.put(
        f"/privacy-settings/trip/{trip_fixture['trip_id']}",
        json={"privacy_type": PrivacyType.private.value},
    )

    assert friend_response.status_code == 403
    assert owner_response.status_code == 200


def test_create_trip_persists_trip_privacy_and_route_stops(api_client, trip_fixture):
    client, test_session, current_user = api_client
    current_user["id"] = trip_fixture["author_id"]

    response = client.post(
        "/trips",
        json={
            "title": "New trip",
            "from_city": {"label": "Origin", "lat": 1.0, "lon": 2.0},
            "to_city": {"label": "Destination", "lat": 3.0, "lon": 4.0},
        },
    )

    assert response.status_code == 201
    response_data = response.json()
    assert response_data["title"] == "New trip"
    assert response_data["message"] == "Trip created successfully"

    with test_session() as db:
        trip = db.query(models.Trip).filter(
            models.Trip.id == response_data["id"]
        ).one()
        privacy = db.query(models.PrivacySettings).filter(
            models.PrivacySettings.entity_type == PrivacyEntityType.trip,
            models.PrivacySettings.entity_id == trip.id,
        ).one()
        stops = db.query(models.Stop).filter(
            models.Stop.trip_id == trip.id
        ).order_by(models.Stop.order).all()

        assert trip.user_id == trip_fixture["author_id"]
        assert privacy.privacy_type == PrivacyType.public
        assert [(stop.title, stop.order) for stop in stops] == [
            ("Origin", 0),
            ("Destination", 1),
        ]


def test_delete_trip_cleans_related_records_and_requires_owner(api_client, trip_fixture):
    client, test_session, current_user = api_client

    current_user["id"] = trip_fixture["friend_id"]
    unauthorized_response = client.delete(
        f"/trips/{trip_fixture['trip_id']}"
    )
    assert unauthorized_response.status_code == 404

    current_user["id"] = trip_fixture["owner_id"]
    response = client.delete(f"/trips/{trip_fixture['trip_id']}")

    assert response.status_code == 200
    assert response.json()["message"] == "Trip deleted successfully"

    with test_session() as db:
        assert db.query(models.Trip).filter(
            models.Trip.id == trip_fixture["trip_id"]
        ).count() == 0
        assert db.query(models.Stop).filter(
            models.Stop.trip_id == trip_fixture["trip_id"]
        ).count() == 0
        assert db.query(models.Post).filter(
            models.Post.id == trip_fixture["post_id"]
        ).count() == 0
        assert db.query(models.PrivacySettings).filter(
            models.PrivacySettings.entity_type == PrivacyEntityType.trip,
            models.PrivacySettings.entity_id == trip_fixture["trip_id"],
        ).count() == 0


def test_friend_trip_list_only_includes_trips_visible_to_friend(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        private_trip = models.Trip(
            user_id=trip_fixture["owner_id"],
            title="Private trip",
        )
        db.add(private_trip)
        db.flush()
        db.add(
            models.PrivacySettings(
                entity_type=PrivacyEntityType.trip,
                entity_id=private_trip.id,
                privacy_type=PrivacyType.private,
            )
        )
        private_trip_id = private_trip.id
        db.commit()

    current_user["id"] = trip_fixture["friend_id"]
    response = client.get(
        f"/trips/friend/{trip_fixture['owner_id']}"
    )

    assert response.status_code == 200
    response_data = response.json()
    assert [trip["id"] for trip in response_data["trips"]] == [
        trip_fixture["trip_id"]
    ]
    assert private_trip_id not in [
        trip["id"] for trip in response_data["trips"]
    ]
    assert response_data["total_records"] == 1


def test_send_friend_request_creates_and_reactivates_refused_request(
    api_client,
    trip_fixture,
    monkeypatch,
):
    client, test_session, current_user = api_client
    notification = Mock()
    monkeypatch.setattr(
        "app.services.friendship_requests.create_and_send_notification",
        notification,
    )

    with test_session() as db:
        statuses = {
            name: models.FriendshipStatus(name=name)
            for name in FriendshipStatusEnum
        }
        first_receiver = models.User(
            email="first-receiver@example.test",
            password="test",
            firstname="First",
            lastname="Receiver",
        )
        second_receiver = models.User(
            email="second-receiver@example.test",
            password="test",
            firstname="Second",
            lastname="Receiver",
        )
        db.add_all([*statuses.values(), first_receiver, second_receiver])
        db.flush()
        refused_request = models.FriendshipRequest(
            sender_id=first_receiver.id,
            receiver_id=trip_fixture["author_id"],
            status_id=statuses[FriendshipStatusEnum.refused].id,
        )
        db.add(refused_request)
        db.commit()
        first_receiver_id = first_receiver.id
        second_receiver_id = second_receiver.id
        refused_request_id = refused_request.id
        pending_status_id = statuses[FriendshipStatusEnum.pending].id

    current_user["id"] = trip_fixture["author_id"]
    reactivated_response = client.post(
        "/friendship-requests",
        json={"receiver_id": first_receiver_id},
    )
    created_response = client.post(
        "/friendship-requests",
        json={"receiver_id": second_receiver_id},
    )
    duplicate_response = client.post(
        "/friendship-requests",
        json={"receiver_id": second_receiver_id},
    )

    assert reactivated_response.status_code == 201
    assert reactivated_response.json()["id"] == refused_request_id
    assert reactivated_response.json()["sender_id"] == trip_fixture["author_id"]
    assert reactivated_response.json()["receiver_id"] == first_receiver_id
    assert reactivated_response.json()["status"] == FriendshipStatusEnum.pending.value
    assert created_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert notification.call_count == 2

    with test_session() as db:
        assert db.query(models.FriendshipRequest).filter(
            models.FriendshipRequest.sender_id == trip_fixture["author_id"],
            models.FriendshipRequest.receiver_id == second_receiver_id,
            models.FriendshipRequest.status_id
            == pending_status_id,
        ).count() == 1


def test_only_request_recipient_can_accept_friend_request(
    api_client,
    trip_fixture,
    monkeypatch,
):
    client, test_session, current_user = api_client
    notification = Mock()
    monkeypatch.setattr(
        "app.services.friendship_requests.create_and_send_notification",
        notification,
    )

    with test_session() as db:
        statuses = {
            name: models.FriendshipStatus(name=name)
            for name in FriendshipStatusEnum
        }
        db.add_all(statuses.values())
        db.flush()
        friend_request = models.FriendshipRequest(
            sender_id=trip_fixture["author_id"],
            receiver_id=trip_fixture["owner_id"],
            status_id=statuses[FriendshipStatusEnum.pending].id,
        )
        db.add(friend_request)
        db.commit()
        request_id = friend_request.id

    current_user["id"] = trip_fixture["author_id"]
    sender_response = client.patch(
        f"/friend-requests/{request_id}/accept"
    )

    current_user["id"] = trip_fixture["owner_id"]
    recipient_response = client.patch(
        f"/friend-requests/{request_id}/accept"
    )

    assert sender_response.status_code == 403
    assert recipient_response.status_code == 200
    assert recipient_response.json()["status"] == FriendshipStatusEnum.accepted.value
    notification.assert_called_once()

    with test_session() as db:
        assert db.query(models.Friendship).filter(
            models.Friendship.user_1_id
            == min(trip_fixture["author_id"], trip_fixture["owner_id"]),
            models.Friendship.user_2_id
            == max(trip_fixture["author_id"], trip_fixture["owner_id"]),
        ).count() == 1
        request = db.query(models.FriendshipRequest).filter(
            models.FriendshipRequest.id == request_id
        ).one()
        assert request.status.name == FriendshipStatusEnum.accepted


def test_only_request_recipient_can_decline_pending_request(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        statuses = {
            name: models.FriendshipStatus(name=name)
            for name in FriendshipStatusEnum
        }
        db.add_all(statuses.values())
        db.flush()
        friend_request = models.FriendshipRequest(
            sender_id=trip_fixture["author_id"],
            receiver_id=trip_fixture["owner_id"],
            status_id=statuses[FriendshipStatusEnum.pending].id,
        )
        db.add(friend_request)
        db.commit()
        request_id = friend_request.id

    current_user["id"] = trip_fixture["author_id"]
    sender_response = client.patch(
        f"/friend-requests/{request_id}/decline"
    )

    current_user["id"] = trip_fixture["owner_id"]
    recipient_response = client.patch(
        f"/friend-requests/{request_id}/decline"
    )
    repeated_response = client.patch(
        f"/friend-requests/{request_id}/decline"
    )

    assert sender_response.status_code == 403
    assert recipient_response.status_code == 200
    assert recipient_response.json()["status"] == FriendshipStatusEnum.refused.value
    assert repeated_response.status_code == 409

    with test_session() as db:
        request = db.query(models.FriendshipRequest).filter(
            models.FriendshipRequest.id == request_id
        ).one()
        assert request.status.name == FriendshipStatusEnum.refused
        assert db.query(models.Friendship).filter(
            models.Friendship.user_1_id
            == min(trip_fixture["author_id"], trip_fixture["owner_id"]),
            models.Friendship.user_2_id
            == max(trip_fixture["author_id"], trip_fixture["owner_id"]),
        ).count() == 0


def test_relationship_status_reports_friendship_and_pending_direction(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        pending_status = models.FriendshipStatus(
            name=FriendshipStatusEnum.pending,
        )
        db.add(pending_status)
        db.flush()
        pending_request = models.FriendshipRequest(
            sender_id=trip_fixture["author_id"],
            receiver_id=trip_fixture["owner_id"],
            status_id=pending_status.id,
        )
        db.add(pending_request)
        db.commit()
        nonexistent_user_id = trip_fixture["author_id"] + 100

    current_user["id"] = trip_fixture["owner_id"]
    friends_response = client.get(
        f"/friendship-status/{trip_fixture['friend_id']}"
    )
    pending_received_response = client.get(
        f"/friendship-status/{trip_fixture['author_id']}"
    )

    current_user["id"] = trip_fixture["author_id"]
    pending_sent_response = client.get(
        f"/friendship-status/{trip_fixture['owner_id']}"
    )
    no_request_response = client.get(
        f"/friendship-status/{trip_fixture['friend_id']}"
    )
    missing_user_response = client.get(
        f"/friendship-status/{nonexistent_user_id}"
    )

    assert friends_response.status_code == 200
    assert friends_response.json()["status"] == "friends"
    assert pending_received_response.json()["status"] == "pending_received"
    assert pending_sent_response.json()["status"] == "pending_sent"
    assert no_request_response.json()["status"] == "none"
    assert missing_user_response.status_code == 404


def test_search_users_returns_relationship_status_and_excludes_friends(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        pending_status = models.FriendshipStatus(
            name=FriendshipStatusEnum.pending,
        )
        sent_candidate = models.User(
            email="post.traveler@example.test",
            password="test",
            firstname="Post",
            lastname="Traveler",
        )
        unrelated_candidate = models.User(
            email="post.stranger@example.test",
            password="test",
            firstname="Post",
            lastname="Stranger",
        )
        trip_candidate = models.User(
            email="trip.traveler@example.test",
            password="test",
            firstname="Trip",
            lastname="Traveler",
        )
        db.add_all(
            [
                pending_status,
                sent_candidate,
                unrelated_candidate,
                trip_candidate,
            ]
        )
        db.flush()
        db.add_all(
            [
                models.FriendshipRequest(
                    sender_id=trip_fixture["author_id"],
                    receiver_id=trip_fixture["owner_id"],
                    status_id=pending_status.id,
                ),
                models.FriendshipRequest(
                    sender_id=trip_fixture["owner_id"],
                    receiver_id=sent_candidate.id,
                    status_id=pending_status.id,
                ),
            ]
        )
        db.commit()
        sent_candidate_id = sent_candidate.id
        unrelated_candidate_id = unrelated_candidate.id
        trip_candidate_id = trip_candidate.id

    current_user["id"] = trip_fixture["owner_id"]
    response = client.get(
        "/users/search",
        params={"query": "Post"},
    )
    friend_and_self_excluded_response = client.get(
        "/users/search",
        params={"query": "Trip"},
    )
    blank_response = client.get(
        "/users/search",
        params={"query": "   "},
    )

    assert response.status_code == 200
    results_by_id = {user["id"]: user for user in response.json()["users"]}
    assert results_by_id[trip_fixture["author_id"]]["relationshipStatus"] == "pending_received"
    assert results_by_id[sent_candidate_id]["relationshipStatus"] == "pending_sent"
    assert results_by_id[unrelated_candidate_id]["relationshipStatus"] == "none"
    assert response.json()["total_records"] == 3

    assert friend_and_self_excluded_response.status_code == 200
    assert [user["id"] for user in friend_and_self_excluded_response.json()["users"]] == [
        trip_candidate_id
    ]
    assert blank_response.status_code == 200
    assert blank_response.json()["users"] == []
    assert blank_response.json()["total_records"] == 0


def test_search_friends_returns_matching_paginated_friends(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        second_friend = models.User(
            email="second.friend@example.test",
            password="test",
            firstname="Second",
            lastname="Friend",
        )
        db.add(second_friend)
        db.flush()
        db.add(
            models.Friendship(
                user_1_id=trip_fixture["owner_id"],
                user_2_id=second_friend.id,
            )
        )
        db.commit()
        second_friend_id = second_friend.id

    current_user["id"] = trip_fixture["owner_id"]
    response = client.get(
        "/Friends/search",
        params={"q": "Friend", "page_number": 2, "page_size": 1},
    )
    non_friend_response = client.get(
        "/Friends/search",
        params={"q": "Author"},
    )
    blank_response = client.get(
        "/Friends/search",
        params={"q": "   "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["friends"]) == 1
    assert payload["friends"][0]["friend_id"] in {
        trip_fixture["friend_id"],
        second_friend_id,
    }
    assert payload["page_number"] == 2
    assert payload["page_size"] == 1
    assert payload["total_records"] == 2
    assert payload["total_pages"] == 2
    assert payload["stops"] == []

    assert non_friend_response.status_code == 200
    assert non_friend_response.json()["friends"] == []
    assert non_friend_response.json()["total_records"] == 0
    assert blank_response.status_code == 200
    assert blank_response.json()["friends"] == []
    assert blank_response.json()["page_number"] == 1
    assert blank_response.json()["page_size"] == 10
    assert blank_response.json()["total_records"] == 0


def test_get_my_friends_returns_paginated_friends_and_404_when_empty(
    api_client,
    trip_fixture,
):
    client, _, current_user = api_client
    current_user["id"] = trip_fixture["owner_id"]

    friends_response = client.get(
        "/Friends/me",
        params={"page_number": 1, "page_size": 1},
    )

    current_user["id"] = trip_fixture["author_id"]
    no_friends_response = client.get("/Friends/me")

    assert friends_response.status_code == 200
    friends_payload = friends_response.json()
    assert friends_payload["data"] == [
        {
            "friend_id": trip_fixture["friend_id"],
            "username": "Trip Friend",
            "profile_picture": None,
        }
    ]
    assert friends_payload["page_number"] == 1
    assert friends_payload["page_size"] == 1
    assert friends_payload["total_records"] == 1
    assert no_friends_response.status_code == 404
    assert no_friends_response.json()["message"] == "No friends found."


def test_delete_friend_removes_friendship_in_either_direction(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client
    current_user["id"] = trip_fixture["friend_id"]

    response = client.delete(f"/Friends/{trip_fixture['owner_id']}")
    missing_friendship_response = client.delete(
        f"/Friends/{trip_fixture['owner_id']}"
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Friend removed successfully."
    assert missing_friendship_response.status_code == 404
    assert missing_friendship_response.json()["message"] == "Friendship not found."

    with test_session() as db:
        assert db.query(models.Friendship).filter(
            models.Friendship.user_1_id == trip_fixture["owner_id"],
            models.Friendship.user_2_id == trip_fixture["friend_id"],
        ).count() == 0


def test_incoming_friend_requests_returns_paginated_sender_details(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        pending_status = models.FriendshipStatus(
            name=FriendshipStatusEnum.pending,
        )
        db.add(pending_status)
        db.flush()
        db.add(
            models.FriendshipRequest(
                sender_id=trip_fixture["author_id"],
                receiver_id=trip_fixture["owner_id"],
                status_id=pending_status.id,
            )
        )
        db.commit()

    current_user["id"] = trip_fixture["owner_id"]
    response = client.get(
        "/friend-requests/incoming",
        params={"page_number": 1, "page_size": 1},
    )
    payload = response.json()

    assert response.status_code == 200
    assert len(payload["requests"]) == 1
    assert payload["requests"][0]["sender_id"] == trip_fixture["author_id"]
    assert payload["requests"][0]["receiver_id"] == trip_fixture["owner_id"]
    assert payload["requests"][0]["status"] == FriendshipStatusEnum.pending.value
    assert payload["requests"][0]["sender_name"] == "Post Author"
    assert payload["requests"][0]["sender_avatar"] is None
    assert payload["page_number"] == 1
    assert payload["page_size"] == 1
    assert payload["total_pages"] == 1
    assert payload["total_records"] == 1


def test_reorder_stops_keeps_departure_and_destination_fixed(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        destination = db.query(models.Stop).filter(
            models.Stop.id == trip_fixture["destination_stop_id"]
        ).one()
        destination.order = 3
        first_city = models.City(lat=70.0, long=80.0)
        second_city = models.City(lat=90.0, long=100.0)
        db.add_all([first_city, second_city])
        db.flush()
        first_middle_stop = models.Stop(
            trip_id=trip_fixture["trip_id"],
            city_id=first_city.id,
            title="First middle stop",
            order=1,
        )
        second_middle_stop = models.Stop(
            trip_id=trip_fixture["trip_id"],
            city_id=second_city.id,
            title="Second middle stop",
            order=2,
        )
        db.add_all([first_middle_stop, second_middle_stop])
        db.commit()
        first_middle_stop_id = first_middle_stop.id
        second_middle_stop_id = second_middle_stop.id

    current_user["id"] = trip_fixture["owner_id"]
    response = client.put(
        f"/trips/{trip_fixture['trip_id']}/stops/reorder",
        json={
            "stop_ids": [
                trip_fixture["departure_stop_id"],
                second_middle_stop_id,
                first_middle_stop_id,
                trip_fixture["destination_stop_id"],
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Stops reordered successfully"

    with test_session() as db:
        stops = db.query(models.Stop).filter(
            models.Stop.trip_id == trip_fixture["trip_id"]
        ).order_by(models.Stop.order).all()

        assert [stop.id for stop in stops] == [
            trip_fixture["departure_stop_id"],
            second_middle_stop_id,
            first_middle_stop_id,
            trip_fixture["destination_stop_id"],
        ]
        assert [stop.order for stop in stops] == [0, 1, 2, 3]


def test_delete_stop_removes_its_posts_and_requires_trip_owner(
    api_client,
    trip_fixture,
):
    client, test_session, current_user = api_client

    with test_session() as db:
        city = models.City(lat=110.0, long=120.0)
        db.add(city)
        db.flush()
        stop = models.Stop(
            trip_id=trip_fixture["trip_id"],
            city_id=city.id,
            title="Stop to delete",
            order=2,
        )
        db.add(stop)
        db.flush()
        post = models.Post(
            stop_id=stop.id,
            user_id=trip_fixture["author_id"],
            title="Post on stop",
        )
        db.add(post)
        db.commit()
        stop_id = stop.id
        post_id = post.id

    current_user["id"] = trip_fixture["friend_id"]
    unauthorized_response = client.delete(f"/stops/{stop_id}")
    assert unauthorized_response.status_code == 403

    current_user["id"] = trip_fixture["owner_id"]
    response = client.delete(f"/stops/{stop_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "Stop deleted successfully"
    assert response.json()["city"]["lat"] == 110.0

    with test_session() as db:
        assert db.query(models.Stop).filter(
            models.Stop.id == stop_id
        ).count() == 0
        assert db.query(models.Post).filter(
            models.Post.id == post_id
        ).count() == 0
