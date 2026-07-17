from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_login_invalid_email():
    response = client.post(
        "/login",
        data={
            "username": "doesnotexist@test.com",
            "password": "password123"
        }
    )

    assert response.status_code == 403
    


    