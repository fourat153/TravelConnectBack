"""Shared fixtures for the test suite.

Uses a dedicated Postgres test database (see root conftest.py for the URL).
The schema is built by running the project's real Alembic migrations once per
test session, so migrations themselves are exercised. Each test then runs
inside a transaction that is rolled back afterwards, keeping tests fast and
isolated without re-running migrations every time.
"""
import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from Dbengin import get_db
from app.main import app

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]


@pytest.fixture(scope="session")
def _engine():
    engine = create_engine(TEST_DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _migrate(_engine):
    """Run Alembic migrations against the test DB once for the whole session.

    We reset by dropping and recreating the `public` schema rather than running
    Alembic downgrades: Postgres ENUM types are not removed by drop_table, so a
    plain downgrade/upgrade cycle leaves orphaned types behind. Recreating the
    schema guarantees a truly clean slate (tables AND types) every run.
    """
    with _engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    alembic_cfg = Config("alembic.ini")
    # alembic/env.py reads connection info from the database_* env vars, which
    # the root conftest already points at the test database.
    command.upgrade(alembic_cfg, "head")
    yield


@pytest.fixture
def db_session(_engine):
    """Per-test session wrapped in a transaction that is rolled back."""
    connection = _engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_session):
    """TestClient with the `get_db` dependency pointed at the test session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
