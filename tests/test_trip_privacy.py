from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.enums import PrivacyEntityType, PrivacyType
from app.models import Friendship, PrivacySettings
from app.services.trip_privacy import (
    can_create_post_on_stop,
    can_delete_post,
    can_modify_stop,
    can_modify_trip,
    can_view_trip,
    get_privacy_entity_owner_id,
    load_trip_visibility_data,
)


class FakeQuery:
    def __init__(self, first_result=None, all_results=None):
        self.first_result = first_result
        self.all_results = all_results or []

    def filter(self, *criteria):
        return self

    def first(self):
        return self.first_result

    def all(self):
        return self.all_results


def make_db(privacy_settings=(), friendships=()):
    db = Mock()

    def query(model):
        if model is PrivacySettings:
            return FakeQuery(
                first_result=privacy_settings[0] if privacy_settings else None,
                all_results=list(privacy_settings),
            )
        if model is Friendship:
            return FakeQuery(all_results=list(friendships))
        raise AssertionError(f"Unexpected model query: {model}")

    db.query.side_effect = query
    return db


def make_trip(owner_id=10, trip_id=1):
    return SimpleNamespace(id=trip_id, user_id=owner_id)


def test_trip_modification_is_limited_to_owner():
    trip = make_trip()

    assert can_modify_trip(trip, 10) is True
    assert can_modify_trip(trip, 20) is False


def test_stop_modification_requires_trip_ownership():
    stop = SimpleNamespace(trip=make_trip())
    orphaned_stop = SimpleNamespace(trip=None)

    assert can_modify_stop(stop, 10) is True
    assert can_modify_stop(stop, 20) is False
    assert can_modify_stop(orphaned_stop, 10) is False


def test_post_creation_on_stop_requires_trip_ownership():
    stop = SimpleNamespace(trip=make_trip())

    assert can_create_post_on_stop(stop, 10) is True
    assert can_create_post_on_stop(stop, 20) is False


def test_post_deletion_remains_limited_to_post_author():
    post = SimpleNamespace(user_id=10)

    assert can_delete_post(post, 10) is True
    assert can_delete_post(post, 20) is False


@pytest.mark.parametrize(
    ("entity_type", "entity", "expected_owner_id"),
    [
        (PrivacyEntityType.user, SimpleNamespace(id=10), 10),
        (PrivacyEntityType.trip, SimpleNamespace(user_id=10), 10),
        (
            PrivacyEntityType.stop,
            SimpleNamespace(trip=SimpleNamespace(user_id=10)),
            10,
        ),
        (
            PrivacyEntityType.post,
            SimpleNamespace(stop=SimpleNamespace(trip=SimpleNamespace(user_id=10))),
            10,
        ),
    ],
)
def test_privacy_entity_owner_lookup_resolves_owner(
    entity_type,
    entity,
    expected_owner_id,
):
    db = Mock()
    db.query.return_value = FakeQuery(first_result=entity)

    assert get_privacy_entity_owner_id(db, entity_type, 1) == expected_owner_id


def test_privacy_entity_owner_lookup_returns_none_for_missing_entity():
    db = Mock()
    db.query.return_value = FakeQuery()

    assert get_privacy_entity_owner_id(db, PrivacyEntityType.trip, 1) is None


@pytest.mark.parametrize(
    ("privacy_type", "viewer_id", "friend_ids", "expected"),
    [
        (PrivacyType.public, 20, set(), True),
        (PrivacyType.private, 20, {10}, False),
        (PrivacyType.friends_only, 20, {10}, True),
        (PrivacyType.friends_only, 20, set(), False),
    ],
)
def test_can_view_trip_applies_privacy_and_friendship_rules(
    privacy_type,
    viewer_id,
    friend_ids,
    expected,
):
    trip = make_trip()
    setting = SimpleNamespace(privacy_type=privacy_type)
    db = make_db(privacy_settings=[setting])

    assert can_view_trip(db, trip, viewer_id, friend_ids) is expected


def test_trip_owner_can_always_view_without_database_queries():
    db = Mock()

    assert can_view_trip(db, make_trip(), 10) is True
    db.query.assert_not_called()


def test_missing_trip_privacy_setting_denies_access():
    db = make_db()

    assert can_view_trip(db, make_trip(), 20) is False


def test_invalid_trip_privacy_value_denies_access():
    setting = SimpleNamespace(privacy_type="invalid")
    db = make_db(privacy_settings=[setting])

    assert can_view_trip(db, make_trip(), 20) is False


def test_can_view_trip_loads_friendships_when_not_preloaded():
    friendship = SimpleNamespace(user_1_id=10, user_2_id=20)
    setting = SimpleNamespace(privacy_type=PrivacyType.friends_only)
    db = make_db(privacy_settings=[setting], friendships=[friendship])

    assert can_view_trip(db, make_trip(), 20) is True


def test_bulk_visibility_context_loads_settings_and_friend_ids():
    trips = [make_trip(owner_id=10, trip_id=1), make_trip(owner_id=30, trip_id=2)]
    settings = [
        SimpleNamespace(entity_id=1, privacy_type=PrivacyType.public),
        SimpleNamespace(entity_id=2, privacy_type=PrivacyType.private),
    ]
    friendships = [SimpleNamespace(user_1_id=20, user_2_id=10)]
    db = make_db(privacy_settings=settings, friendships=friendships)

    privacy_by_trip, friend_ids = load_trip_visibility_data(db, trips, 20)

    assert set(privacy_by_trip) == {1, 2}
    assert friend_ids == {10}
    assert can_view_trip(db, trips[0], 20, friend_ids, privacy_by_trip) is True
    assert can_view_trip(db, trips[1], 20, friend_ids, privacy_by_trip) is False
    assert db.query.call_count == 2
