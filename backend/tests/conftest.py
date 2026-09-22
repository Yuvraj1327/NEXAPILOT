"""
Pytest fixtures for API smoke tests.

Runs against a real Postgres database (NEXAPILOT_TEST_DATABASE_URL, or a
`_test` suffixed sibling of DATABASE_URL by default) — not SQLite — so the
tests exercise the exact dialect (UUID, JSON, enums-as-varchar) that
Supabase/production Postgres will use. Schema is created and dropped once
per test session via Base.metadata, independent of Alembic migration
state, so tests don't depend on migrations having been run first.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault(
    "DATABASE_URL",
    os.environ.get(
        "NEXAPILOT_TEST_DATABASE_URL",
        "postgresql+psycopg2://postgres:postgres@localhost:5432/nexapilot_test",
    ),
)

from app.db.base import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app import models as _models  # noqa: E402,F401  (populates Base.metadata)


@pytest.fixture(scope="session")
def engine():
    test_db_url = os.environ["DATABASE_URL"]
    eng = create_engine(test_db_url)
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    TestingSessionLocal = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = _override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
