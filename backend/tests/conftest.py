"""Test fixtures.

The app targets PostgreSQL in production (see app/database.py), but
these tests run against an isolated in-memory SQLite database per test
via dependency override — standard practice for exercising
SQLAlchemy/FastAPI CRUD logic without a live Postgres server.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    # Not entered as a context manager: that would run the app's lifespan,
    # which creates tables against the real (Postgres) engine. Tests create
    # their own tables above, against the SQLite test engine, instead.
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
