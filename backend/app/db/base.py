"""
SQLAlchemy engine, session factory, and declarative base.

Targets Supabase PostgreSQL in every real environment. The engine is
configured defensively for Supabase's connection poolers:

- Session pooler (port 5432): behaves like a normal Postgres connection,
  the default SQLAlchemy QueuePool works fine.
- Transaction pooler / pgbouncer transaction mode (port 6543): does not
  support session-level state across statements, so SQLAlchemy's own
  connection pooling must be disabled (DB_USE_NULLPOOL=true) and let
  pgbouncer do the pooling instead.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

_engine_kwargs = {
    "echo": settings.db_echo,
    "pool_pre_ping": True,  # avoids using dead connections after a DB restart/idle timeout
}
if settings.db_use_nullpool:
    _engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""

    pass


def get_db() -> Session:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
