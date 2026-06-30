"""Unit tests -- no DB, no HTTP. Pure function behavior."""
import pytest
from jose import jwt

from app.utils import oauth2


@pytest.mark.unit
def test_create_access_token_roundtrip():
    token = oauth2.create_access_token({"user": {"id": 42}})
    payload = jwt.decode(token, oauth2.SECRET_KEY, algorithms=[oauth2.ALGORITHM])
    assert payload["user"]["id"] == 42
    assert "exp" in payload
   