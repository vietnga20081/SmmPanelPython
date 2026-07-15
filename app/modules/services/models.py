"""ORM models for the services module: Platform -> Category -> Service."""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Platform(Base):
    """A standard social platform (Facebook, TikTok, YouTube, ...)."""

    __tablename__ = "platforms"
    __table_args__ = (Index("ix_platforms_slug", "slug", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    categories: Mapped[list["Category"]] = relationship(back_populates="platform")


class Category(Base):
    """A service type within a platform (Like, Comment, Follow, View, ...)."""

    __tablename__ = "categories"
    __table_args__ = (Index("ix_categories_platform_name", "platform_id", "name", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform_id: Mapped[int] = mapped_column(ForeignKey("platforms.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    platform: Mapped["Platform"] = relationship(back_populates="categories")


class Service(Base):
    """A sellable catalog entry, synced from and fulfilled by a Provider."""

    __tablename__ = "services"
    __table_args__ = (
        Index("ix_services_provider_ref", "provider_id", "provider_service_ref", unique=True),
        Index("ix_services_platform", "platform_id"),
        Index("ix_services_category", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id", ondelete="CASCADE"), nullable=False)
    provider_service_ref: Mapped[str] = mapped_column(String(50), nullable=False)

    platform_id: Mapped[int | None] = mapped_column(ForeignKey("platforms.id", ondelete="SET NULL"), nullable=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)

    name: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_provider_name: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_provider_category: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    provider_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    min_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    supports_refill: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_cancel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_dripfeed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    platform_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    category_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    price_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    platform: Mapped["Platform | None"] = relationship()
    category: Mapped["Category | None"] = relationship()
