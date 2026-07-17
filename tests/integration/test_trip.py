
import pytest

from app.enums import AccountStatusEnum, ConfirmedEnum, GenderEnum, PrivacyEntityType, PrivacyType
from app.models import City, Stop, Trip, User, PrivacySettings, Friendship
from app.utils.general_util import hash_password


def _create_user(db_session, *, email: str) -> User:
    user = User(
        email=email,
        password=hash_password("password123"),
        firstname="Test",
        lastname="User",
        gender=GenderEnum.male,
        status=AccountStatusEnum.active,
        is_confirmed=ConfirmedEnum.Confirmed,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Add user privacy settings (since create trip expects this)
    user_privacy = PrivacySettings(
        entity_type=PrivacyEntityType.user,
        entity_id=user.id,
        privacy_type=PrivacyType.public,
    )
    db_session.add(user_privacy)
    db_session.commit()

    return user


def _login(client, email: str) -> None:
    response = client.post(
        "/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200


def _create_friendship(db_session, user_1_id: int, user_2_id: int):
    friendship = Friendship(user_1_id=user_1_id, user_2_id=user_2_id)
    db_session.add(friendship)
    db_session.commit()
    db_session.refresh(friendship)
    return friendship


def _create_trip_with_stops(db_session, *, user_id: int, title: str = "Test Trip"):
    trip = Trip(user_id=user_id, title=title)
    db_session.add(trip)
    db_session.flush()

    departure_city = City(lat=10.0, long=20.0)
    destination_city = City(lat=12.0, long=22.0)
    db_session.add_all([departure_city, destination_city])
    db_session.flush()

    departure_stop = Stop(
        trip_id=trip.id,
        city_id=departure_city.id,
        title="Departure",
        order=0,
    )
    destination_stop = Stop(
        trip_id=trip.id,
        city_id=destination_city.id,
        title="Destination",
        order=1,
    )
    db_session.add_all([departure_stop, destination_stop])
    db_session.commit()
    db_session.refresh(trip)
    return trip, departure_stop, destination_stop


@pytest.mark.integration
def test_create_trip_success(client, db_session):
    user = _create_user(db_session, email="trip-create@test.com")
    _login(client, user.email)

    response = client.post(
        "/trips",
        json={
            "title": "My First Trip",
            "from_city": {"lat": 40.7128, "lon": -74.0060, "label": "New York"},
            "to_city": {"lat": 34.0522, "lon": -118.2437, "label": "Los Angeles"},
        },
    )
    data = response.json()

    assert response.status_code == 201
    assert data["status_code"] == 201
    assert data["message"] == "Trip created successfully"
    assert data["id"] != 0
    assert data["title"] == "My First Trip"

    # Verify trip exists in db
    trip = db_session.query(Trip).filter(Trip.id == data["id"]).first()
    assert trip is not None
    assert trip.user_id == user.id
    assert trip.title == "My First Trip"

    # Verify stops are created
    stops = db_session.query(Stop).filter(Stop.trip_id == trip.id).order_by(Stop.order).all()
    assert len(stops) == 2
    assert stops[0].title == "New York"
    assert stops[0].order == 0
    assert stops[1].title == "Los Angeles"
    assert stops[1].order == 1

    # Verify privacy settings are created
    trip_privacy = db_session.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.trip,
        PrivacySettings.entity_id == trip.id,
    ).first()
    assert trip_privacy is not None
    assert trip_privacy.privacy_type == PrivacyType.public


@pytest.mark.integration
def test_get_my_trips_returns_user_trips(client, db_session):
    user = _create_user(db_session, email="my-trips@test.com")
    _login(client, user.email)

    # Create two trips for user
    trip1, _, _ = _create_trip_with_stops(db_session, user_id=user.id, title="Trip 1")
    trip2, _, _ = _create_trip_with_stops(db_session, user_id=user.id, title="Trip 2")

    # Create trip for another user (should not be included)
    other_user = _create_user(db_session, email="other@test.com")
    _create_trip_with_stops(db_session, user_id=other_user.id, title="Other's Trip")

    response = client.get("/trips/me")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Trips retrieved successfully"
    assert len(data["trips"]) == 2
    trip_ids = [t["id"] for t in data["trips"]]
    assert trip1.id in trip_ids
    assert trip2.id in trip_ids


@pytest.mark.integration
def test_get_my_trips_empty_when_no_trips(client, db_session):
    user = _create_user(db_session, email="empty-trips@test.com")
    _login(client, user.email)

    response = client.get("/trips/me")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "No trips found"
    assert len(data["trips"]) == 0


@pytest.mark.integration
def test_get_friend_trips_requires_friendship(client, db_session):
    user = _create_user(db_session, email="friend-trips-user@test.com")
    friend = _create_user(db_session, email="friend-trips-friend@test.com")
    _login(client, user.email)

    # No friendship yet
    response = client.get(f"/trips/friend/{friend.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 403
    assert data["message"] == "You are not friends with this user."
    assert len(data["trips"]) == 0

    # Create friendship, create a trip for friend, then try again
    _create_friendship(db_session, user_1_id=user.id, user_2_id=friend.id)
    _create_trip_with_stops(db_session, user_id=friend.id, title="Friend's Trip")
    response = client.get(f"/trips/friend/{friend.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Trips retrieved successfully"


@pytest.mark.integration
def test_get_friend_trips_returns_friends_trips(client, db_session):
    user = _create_user(db_session, email="friend-trips-1@test.com")
    friend = _create_user(db_session, email="friend-trips-2@test.com")
    _create_friendship(db_session, user_1_id=user.id, user_2_id=friend.id)
    _login(client, user.email)

    trip, _, _ = _create_trip_with_stops(db_session, user_id=friend.id, title="Friend's Trip")

    response = client.get(f"/trips/friend/{friend.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert len(data["trips"]) == 1
    assert data["trips"][0]["id"] == trip.id
    assert data["trips"][0]["title"] == "Friend's Trip"


@pytest.mark.integration
def test_get_friend_first_stop_success(client, db_session):
    user = _create_user(db_session, email="first-stop-user@test.com")
    friend = _create_user(db_session, email="first-stop-friend@test.com")
    _create_friendship(db_session, user_1_id=user.id, user_2_id=friend.id)
    _login(client, user.email)

    trip, departure_stop, _ = _create_trip_with_stops(db_session, user_id=friend.id)

    response = client.get(f"/trips/friend/{friend.id}/first-stop")
    data = response.json()

    assert response.status_code == 200
    assert data["lat"] == departure_stop.city.lat
    assert data["lon"] == departure_stop.city.long
    assert data["stop_title"] == departure_stop.title


@pytest.mark.integration
def test_get_friend_first_stop_no_trips_returns_404(client, db_session):
    user = _create_user(db_session, email="first-stop-no-trips-1@test.com")
    friend = _create_user(db_session, email="first-stop-no-trips-2@test.com")
    _create_friendship(db_session, user_1_id=user.id, user_2_id=friend.id)
    _login(client, user.email)

    response = client.get(f"/trips/friend/{friend.id}/first-stop")
    assert response.status_code == 404
    assert response.json()["detail"] == "Friend has no trips"


@pytest.mark.integration
def test_delete_trip_success(client, db_session):
    user = _create_user(db_session, email="delete-trip@test.com")
    _login(client, user.email)

    trip, departure_stop, _ = _create_trip_with_stops(db_session, user_id=user.id)
    # Also create privacy settings for trip (as delete expects to delete this)
    trip_privacy = PrivacySettings(
        entity_type=PrivacyEntityType.trip,
        entity_id=trip.id,
        privacy_type=PrivacyType.public,
    )
    db_session.add(trip_privacy)
    db_session.commit()

    response = client.delete(f"/trips/{trip.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Trip deleted successfully"
    assert data["id"] == trip.id

    # Verify trip, stops, and privacy settings are deleted
    deleted_trip = db_session.query(Trip).filter(Trip.id == trip.id).first()
    deleted_stops = db_session.query(Stop).filter(Stop.trip_id == trip.id).all()
    deleted_privacy = db_session.query(PrivacySettings).filter(
        PrivacySettings.entity_type == PrivacyEntityType.trip,
        PrivacySettings.entity_id == trip.id,
    ).first()

    assert deleted_trip is None
    assert len(deleted_stops) == 0
    assert deleted_privacy is None


@pytest.mark.integration
def test_delete_trip_not_found_returns_404(client, db_session):
    user = _create_user(db_session, email="delete-404@test.com")
    _login(client, user.email)

    response = client.delete("/trips/99999")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 404
    assert data["message"] == "Trip not found"


@pytest.mark.integration
def test_delete_trip_wrong_user_cannot_delete(client, db_session):
    user1 = _create_user(db_session, email="delete-wrong-1@test.com")
    user2 = _create_user(db_session, email="delete-wrong-2@test.com")
    _login(client, user1.email)

    trip, _, _ = _create_trip_with_stops(db_session, user_id=user2.id)

    response = client.delete(f"/trips/{trip.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 404
    assert data["message"] == "Trip not found"

    # Verify trip still exists
    existing_trip = db_session.query(Trip).filter(Trip.id == trip.id).first()
    assert existing_trip is not None

