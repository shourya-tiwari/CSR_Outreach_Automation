"""SQLAlchemy engine/session setup.

Targets PostgreSQL in normal operation (DATABASE_URL from config/.env).
Tests override `get_db` with an in-memory SQLite engine — see
backend/tests/conftest.py — so the same models/CRUD code is exercised
without requiring a running Postgres instance.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
