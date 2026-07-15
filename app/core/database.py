"""SQLAlchemy engine/session setup optimized for SQLite (WAL mode)."""
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    """Apply per-connection PRAGMAs required for SQLite performance."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA cache_size=-64000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.execute("PRAGMA mmap_size=268435456")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def _create_engine() -> Engine:
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False, "timeout": 5},
        pool_pre_ping=True,
        future=True,
    )


engine: Engine = _create_engine()
event.listen(engine, "connect", _apply_sqlite_pragmas)
SessionLocal: sessionmaker = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_engine() -> None:
    """Kept for backward compatibility; the engine is created eagerly at import time."""
    return None


def optimize_sqlite() -> None:
    """Run PRAGMA optimize; call periodically (e.g. from a scheduled job)."""
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA optimize")


def vacuum_sqlite() -> None:
    """Run VACUUM to reclaim space and defragment the database file."""
    with engine.connect() as conn:
        conn.exec_driver_sql("VACUUM")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for short-lived transactions outside of requests (e.g. jobs)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
