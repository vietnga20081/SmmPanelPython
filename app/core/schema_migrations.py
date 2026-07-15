"""Lightweight SQLite schema migrations.

`Base.metadata.create_all()` only creates missing TABLES, it never adds
columns to a table that already exists — so when a phase adds a new column
to an existing model, an already-deployed database needs a real ALTER TABLE.

This project intentionally does not set up full Alembic migrations (keeps
aaPanel deployment to "copy files, restart" with no extra migration command
to run). Instead, every ad hoc column addition across phases is listed here
and applied idempotently at startup, right after `create_all()`.

Format: (table, column, sqlite_column_ddl). sqlite_column_ddl must include a
DEFAULT so existing rows get a valid value.
"""
from sqlalchemy import text
from sqlalchemy.engine import Engine

_COLUMN_MIGRATIONS: list[tuple[str, str, str]] = [
    # Phase 6: per-provider default markup %, applied when syncing services.
    ("providers", "markup_percent", "FLOAT NOT NULL DEFAULT 0"),
    # Phase 6: locks a service's sell_price against being recalculated on sync,
    # same pattern as platform_locked / category_locked from Phase 5.
    ("services", "price_locked", "BOOLEAN NOT NULL DEFAULT 0"),
]


def _existing_columns(engine: Engine, table: str) -> set[str]:
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _table_exists(engine: Engine, table: str) -> bool:
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table}
        ).fetchone()
    return result is not None


def apply_schema_migrations(engine: Engine) -> None:
    """Add any missing columns listed in `_COLUMN_MIGRATIONS`. Safe to call every startup."""
    for table, column, ddl in _COLUMN_MIGRATIONS:
        if not _table_exists(engine, table):
            continue  # table will be created fresh with the column already in the model
        if column in _existing_columns(engine, table):
            continue
        with engine.begin() as conn:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
