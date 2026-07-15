"""ORM model for the providers module."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Provider(Base):
    """A configured external SMM provider account."""

    __tablename__ = "providers"
    __table_args__ = (Index("ix_providers_name", "name", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    driver: Mapped[str] = mapped_column(String(50), nullable=False)
    api_url: Mapped[str] = mapped_column(String(500), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    markup_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cached_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    cached_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
