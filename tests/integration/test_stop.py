import pytest

from app.enums import AccountStatusEnum, ConfirmedEnum, GenderEnum
from app.models import City, Stop, Trip, User
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
    return user


def _login(client, email: str) -> None:
    response = client.post(
        "/login",
        data={"username": email, "password": "password123"},
    )
    assert response.status_code == 200


def _create_trip_with_stops(db_session, *, user_id: int, title: str = "Test Trip"):
    trip = Trip(user_id=user_id, title=title)
    db_session.add(trip)
    db_session.flush()

    departure_city = City(lat=10.0, long=20.0)
    mid_city = City(lat=11.0, long=21.0)
    destination_city = City(lat=12.0, long=22.0)
    db_session.add_all([departure_city, mid_city, destination_city])
    db_session.flush()

    departure_stop = Stop(
        trip_id=trip.id,
        city_id=departure_city.id,
        title="Departure",
        order=0,
    )
    middle_stop = Stop(
        trip_id=trip.id,
        city_id=mid_city.id,
        title="Middle",
        order=1,
    )
    destination_stop = Stop(
        trip_id=trip.id,
        city_id=destination_city.id,
        title="Destination",
        order=2,
    )
    db_session.add_all([departure_stop, middle_stop, destination_stop])
    db_session.commit()
    db_session.refresh(trip)
    db_session.refresh(departure_stop)
    db_session.refresh(middle_stop)
    db_session.refresh(destination_stop)
    return trip, departure_stop, middle_stop, destination_stop


@pytest.mark.integration
def test_get_trip_stops_returns_ordered_stops(client, db_session):
    user = _create_user(db_session, email="stops-get@test.com")
    trip, departure_stop, middle_stop, destination_stop = _create_trip_with_stops(
        db_session,
        user_id=user.id,
    )

    _login(client, user.email)

    response = client.get(f"/trips/{trip.id}/stops")
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Stops retrieved successfully"
    assert [stop["id"] for stop in data["stops"]] == [
        departure_stop.id,
        middle_stop.id,
        destination_stop.id,
    ]


@pytest.mark.integration
def test_add_stop_inserts_between_departure_and_destination(client, db_session):
    user = _create_user(db_session, email="stops-add@test.com")
    trip, departure_stop, middle_stop, destination_stop = _create_trip_with_stops(
        db_session,
        user_id=user.id,
    )

    _login(client, user.email)

    response = client.post(
        f"/trips/{trip.id}/stops",
        json={
            "lat": 13.0,
            "long": 23.0,
            "title": "New Stop",
            "description": "Added by test",
            "order": 2,
        },
    )
    data = response.json()

    assert response.status_code == 201
    assert data["status_code"] == 201
    assert data["message"] == "Stop added successfully"
    assert data["order"] == 2

    stops = db_session.query(Stop).filter(Stop.trip_id == trip.id).order_by(Stop.order).all()
    assert [stop.order for stop in stops] == [0, 1, 2, 3]
    assert [stop.title for stop in stops] == ["Departure", "Middle", "New Stop", "Destination"]


@pytest.mark.integration
def test_reorder_stops_updates_order_and_keeps_endpoints(client, db_session):
    user = _create_user(db_session, email="stops-reorder@test.com")
    trip = Trip(user_id=user.id, title="Reorder Trip")
    db_session.add(trip)
    db_session.flush()

    city_1 = City(lat=10.0, long=20.0)
    city_2 = City(lat=11.0, long=21.0)
    city_3 = City(lat=12.0, long=22.0)
    city_4 = City(lat=13.0, long=23.0)
    db_session.add_all([city_1, city_2, city_3, city_4])
    db_session.flush()

    departure_stop = Stop(trip_id=trip.id, city_id=city_1.id, title="Departure", order=0)
    first_middle_stop = Stop(trip_id=trip.id, city_id=city_2.id, title="First Middle", order=1)
    second_middle_stop = Stop(trip_id=trip.id, city_id=city_3.id, title="Second Middle", order=2)
    destination_stop = Stop(trip_id=trip.id, city_id=city_4.id, title="Destination", order=3)
    db_session.add_all([departure_stop, first_middle_stop, second_middle_stop, destination_stop])
    db_session.commit()

    _login(client, user.email)

    response = client.put(
        f"/trips/{trip.id}/stops/reorder",
        json={
            "stop_ids": [
                departure_stop.id,
                second_middle_stop.id,
                first_middle_stop.id,
                destination_stop.id,
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Stops reordered successfully"

    stops = db_session.query(Stop).filter(Stop.trip_id == trip.id).order_by(Stop.order).all()
    assert [stop.id for stop in stops] == [
        departure_stop.id,
        second_middle_stop.id,
        first_middle_stop.id,
        destination_stop.id,
    ]
    assert [stop.order for stop in stops] == [0, 1, 2, 3]


@pytest.mark.integration
def test_reorder_stops_rejects_duplicate_ids(client, db_session):
    user = _create_user(db_session, email="stops-reorder-invalid@test.com")
    trip, departure_stop, middle_stop, destination_stop = _create_trip_with_stops(
        db_session,
        user_id=user.id,
    )

    _login(client, user.email)

    response = client.put(
        f"/trips/{trip.id}/stops/reorder",
        json={
            "stop_ids": [
                departure_stop.id,
                middle_stop.id,
                middle_stop.id,
                destination_stop.id,
            ],
        },
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status_code"] == 400
    assert data["message"] == "Duplicate stop ids are not allowed"