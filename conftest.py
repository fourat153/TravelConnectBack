"""Root conftest.

Loaded by pytest before any test module is imported.

We point the application and Alembic at a dedicated **Postgres test
database** (not the dev one). The URL is taken from the TEST_DATABASE_URL
environment variable; if unset it defaults to your normal database name with a
`_test` suffix, using the same credentials from your .env.

Create the database once before running tests, e.g.:
    createdb <database_name>_test
or in psql:
    CREATE DATABASE <database_name>_test;
"""
import os

from dotenv import load_dotenv

# Load the real .env so we can reuse credentials / host for the test DB.
load_dotenv()


def _build_default_url() -> str:
    user = os.getenv("database_username", "postgres")
    pwd = os.getenv("database_password", "")
    host = os.getenv("database_hostname", "localhost")
    port = os.getenv("database_port", "5432")
    name = os.getenv("database_name", "postgres")
    return f"postgresql://{user}:{pwd}@{host}:{port}/{name}_test"


# Single source of truth for the test database URL.
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or _build_default_url()
os.environ["TEST_DATABASE_URL"] = TEST_DATABASE_URL

# app.config.Settings (pydantic-settings) requires these at import time, and
# alembic/env.py builds its URL from these individual vars. Override them so
# *everything* -- app engine and migrations -- targets the test database.
from urllib.parse import urlparse

_parsed = urlparse(TEST_DATABASE_URL)
os.environ["database_username"] = _parsed.username or ""
os.environ["database_password"] = _parsed.password or ""
os.environ["database_hostname"] = _parsed.hostname or "localhost"
os.environ["database_port"] = str(_parsed.port or 5432)
os.environ["database_name"] = (_parsed.path or "/").lstrip("/")

# Pydantic Settings reads these (uppercase or lowercase both resolve); set the
# remaining required non-DB settings so import never fails in CI.
os.environ.setdefault("secret_key", "test-secret-key")
os.environ.setdefault("algorithm", "HS256")
os.environ.setdefault("access_token_expire_min", "30")
os.environ.setdefault("CLOUDINARY_CLOUD_NAME", "test")
os.environ.setdefault("CLOUDINARY_API_KEY", "test")
os.environ.setdefault("CLOUDINARY_API_SECRET", "test")
