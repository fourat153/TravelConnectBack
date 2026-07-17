from datetime import datetime, timedelta

import pytest
from app.enums import AccountStatusEnum, CodeStatus, ConfirmedEnum, GenderEnum
from app.models import ConfirmationCode, User
from app.utils.general_util import hash_password


def _create_user(
    db_session,
    *,
    email: str,
    confirmed: ConfirmedEnum = ConfirmedEnum.Confirmed,
) -> User:
    user = User(
        email=email,
        password=hash_password("password123"),
        firstname="Test",
        lastname="User",
        gender=GenderEnum.male,
        is_confirmed=confirmed,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.integration
def test_login_with_unknown_email(client):
    response = client.post(
        "/login",
        data={"username": "unknown@test.com", "password": "password123"},
    )

    data = response.json()
    assert data["status_code"] == 403
    assert data["message"] == "Invalid Credentials"


@pytest.mark.integration
def test_login_rejects_unconfirmed_user(client, db_session):
    _create_user(
        db_session,
        email="not-confirmed@test.com",
        confirmed=ConfirmedEnum.NotConfirmed,
    )

    response = client.post(
        "/login",
        data={"username": "not-confirmed@test.com", "password": "password123"},
    )

    data = response.json()
    assert data["status_code"] == 403
    assert data["message"] == "Email has not been verified yet"


@pytest.mark.integration
def test_login_rejects_wrong_password(client, db_session):
    _create_user(db_session, email="test@test.com")

    response = client.post(
        "/login",
        data={"username": "test@test.com", "password": "wrong-password"},
    )

    data = response.json()
    assert data["status_code"] == 403
    assert data["message"] == "Invalid Credentials"


@pytest.mark.integration
def test_login_success_sets_cookie_and_returns_token(client, db_session):
    user = _create_user(db_session, email="confirmed@test.com")

    response = client.post(
        "/login",
        data={"username": "confirmed@test.com", "password": "password123"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Login successful"
    assert data["id"] == user.id
    assert data["email"] == user.email
    assert "access_token" in response.cookies


@pytest.mark.integration
def test_confirm_account_with_invalid_code(client, db_session):
    user = _create_user(
        db_session,
        email="confirm-invalid@test.com",
        confirmed=ConfirmedEnum.NotConfirmed,
    )

    response = client.patch(
        "/confirmAccount",
        json={"user_id": user.id, "confirmation_code": "bad-code"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["status_code"] == 400
    assert data["message"] == "Invalid confirmation code"


@pytest.mark.integration
def test_confirm_account_with_mismatched_user(client, db_session):
    code_owner = _create_user(
        db_session,
        email="code-owner@test.com",
        confirmed=ConfirmedEnum.NotConfirmed,
    )
    another_user = _create_user(
        db_session,
        email="another-user@test.com",
        confirmed=ConfirmedEnum.NotConfirmed,
    )
    code = ConfirmationCode(
        user_id=code_owner.id,
        code="MISMATCH123",
        email=code_owner.email,
        status=CodeStatus.pending,
        expires_at=datetime.now() + timedelta(minutes=10),
        created_at=datetime.now(),
    )
    db_session.add(code)
    db_session.commit()

    response = client.patch(
        "/confirmAccount",
        json={"user_id": another_user.id, "confirmation_code": "MISMATCH123"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["status_code"] == 400
    assert data["message"] == "Confirmation code does not match user"


@pytest.mark.integration
def test_confirm_account_success_updates_user_and_code(client, db_session):
    user = _create_user(
        db_session,
        email="confirm-success@test.com",
        confirmed=ConfirmedEnum.NotConfirmed,
    )
    code = ConfirmationCode(
        user_id=user.id,
        code="VALID123",
        email=user.email,
        status=CodeStatus.pending,
        expires_at=datetime.now() + timedelta(minutes=10),
        created_at=datetime.now(),
    )
    db_session.add(code)
    db_session.commit()

    response = client.patch(
        "/confirmAccount",
        json={"user_id": user.id, "confirmation_code": "VALID123"},
    )

    data = response.json()
    assert response.status_code == 200
    assert data["status_code"] == 200
    assert data["message"] == "Account Confirmed"

    db_session.refresh(user)
    db_session.refresh(code)
    assert user.is_confirmed == ConfirmedEnum.Confirmed
    assert user.status == AccountStatusEnum.active
    assert code.status == CodeStatus.used


@pytest.mark.integration
def test_verify_session_requires_auth(client):
    response = client.get("/auth/verify")
    assert response.status_code == 401
    assert response.json()["detail"] == "Could not validate credentials"


@pytest.mark.integration
def test_verify_session_success_after_login(client, db_session):
    _create_user(db_session, email="verify@test.com")

    login_response = client.post(
        "/login",
        data={"username": "verify@test.com", "password": "password123"},
    )
    assert login_response.status_code == 200

    verify_response = client.get("/auth/verify")
    assert verify_response.status_code == 200
    assert verify_response.json() == {"valid": True}


@pytest.mark.integration
def test_logout_success(client, db_session):
    _create_user(db_session, email="logout@test.com")

    login_response = client.post(
        "/login",
        data={"username": "logout@test.com", "password": "password123"},
    )
    assert login_response.status_code == 200

    logout_response = client.post("/logout")
    assert logout_response.status_code == 200
    assert logout_response.json()["message"] == "Logout successful"

    verify_response = client.get("/auth/verify")
    assert verify_response.status_code == 401
    