"""SQLAlchemy engine, session factory and schema initialisation.

Schema management for the hackathon build is `create_all` at start-up (idempotent);
Alembic migrations are on the roadmap in ARCHITECTURE.md.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def _ensure_sqlite_dir(url: str) -> None:
    if url.startswith("sqlite:///") and ":memory:" not in url:
        Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)


def configure_engine(url: str | None = None) -> Engine:
    """(Re)create the engine. Tests call this with a temporary database URL."""
    global _engine, _SessionLocal
    database_url = url or get_settings().database_url
    _ensure_sqlite_dir(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    _engine = create_engine(database_url, connect_args=connect_args, future=True)

    if database_url.startswith("sqlite"):

        @event.listens_for(_engine, "connect")
        def _sqlite_pragmas(dbapi_connection, _record):  # type: ignore[no-untyped-def]
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, expire_on_commit=False)
    return _engine


def get_engine() -> Engine:
    return _engine or configure_engine()


def init_db() -> None:
    from app import models  # noqa: F401  (register tables)

    Base.metadata.create_all(get_engine())


def session_factory() -> sessionmaker[Session]:
    if _SessionLocal is None:
        configure_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Iterator[Session]:
    db = session_factory()()
    try:
        yield db
    finally:
        db.close()
