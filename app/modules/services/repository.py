"""Repository layer for the services module."""
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.services.classifier import slugify
from app.modules.services.models import Category, Platform, Service

PAGE_SIZE = 15


class PlatformRepository:
    """CRUD + get-or-create for Platform."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Platform]:
        stmt = select(Platform).order_by(Platform.sort_order, Platform.name)
        return list(self._db.execute(stmt).scalars().all())

    def get_by_id(self, platform_id: int) -> Platform | None:
        return self._db.get(Platform, platform_id)

    def get_by_name(self, name: str) -> Platform | None:
        stmt = select(Platform).where(Platform.name == name).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, name: str, sort_order: int = 999) -> Platform:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        platform = Platform(name=name, slug=slugify(name), sort_order=sort_order)
        self._db.add(platform)
        self._db.commit()
        self._db.refresh(platform)
        return platform


class CategoryRepository:
    """CRUD + get-or-create for Category, scoped to a Platform."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_platform_and_name(self, platform_id: int, name: str) -> Category | None:
        stmt = select(Category).where(Category.platform_id == platform_id, Category.name == name).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, platform_id: int, name: str) -> Category:
        existing = self.get_by_platform_and_name(platform_id, name)
        if existing is not None:
            return existing
        category = Category(platform_id=platform_id, name=name, slug=slugify(name))
        self._db.add(category)
        self._db.commit()
        self._db.refresh(category)
        return category

    def list_by_platform(self, platform_id: int) -> list[Category]:
        stmt = select(Category).where(Category.platform_id == platform_id).order_by(Category.name)
        return list(self._db.execute(stmt).scalars().all())

    def list_all(self) -> list[Category]:
        stmt = select(Category).order_by(Category.platform_id, Category.name)
        return list(self._db.execute(stmt).scalars().all())


class ServiceRepository:
    """Search, paginate, upsert Service rows synced from providers."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, service_id: int) -> Service | None:
        return self._db.get(Service, service_id)

    def get_by_provider_ref(self, provider_id: int, provider_service_ref: str) -> Service | None:
        stmt = select(Service).where(
            Service.provider_id == provider_id, Service.provider_service_ref == provider_service_ref
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def search_paginated(
        self,
        q: str,
        platform_id: int | None,
        category_id: int | None,
        provider_id: int | None,
        status: str,
        page: int,
        page_size: int = PAGE_SIZE,
    ) -> tuple[list[Service], int]:
        stmt = select(Service)
        count_stmt = select(func.count()).select_from(Service)

        if q:
            like = f"%{q}%"
            condition = or_(Service.name.ilike(like), Service.raw_provider_name.ilike(like))
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        if platform_id is not None:
            stmt = stmt.where(Service.platform_id == platform_id)
            count_stmt = count_stmt.where(Service.platform_id == platform_id)
        if category_id is not None:
            stmt = stmt.where(Service.category_id == category_id)
            count_stmt = count_stmt.where(Service.category_id == category_id)
        if provider_id is not None:
            stmt = stmt.where(Service.provider_id == provider_id)
            count_stmt = count_stmt.where(Service.provider_id == provider_id)
        if status == "active":
            stmt = stmt.where(Service.is_active.is_(True))
            count_stmt = count_stmt.where(Service.is_active.is_(True))
        elif status == "inactive":
            stmt = stmt.where(Service.is_active.is_(False))
            count_stmt = count_stmt.where(Service.is_active.is_(False))

        total = self._db.execute(count_stmt).scalar_one()
        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(Service.id.desc()).offset(offset).limit(page_size)
        items = list(self._db.execute(stmt).scalars().all())
        return items, total

    def count_by_platform(self) -> list[tuple[str, int]]:
        stmt = (
            select(Platform.name, func.count(Service.id))
            .join(Service, Service.platform_id == Platform.id)
            .group_by(Platform.name)
            .order_by(func.count(Service.id).desc())
        )
        return list(self._db.execute(stmt).all())

    def count_total(self) -> int:
        return self._db.execute(select(func.count()).select_from(Service)).scalar_one()

    def count_active(self) -> int:
        stmt = select(func.count()).select_from(Service).where(Service.is_active.is_(True))
        return self._db.execute(stmt).scalar_one()

    def create(self, **fields) -> Service:
        service = Service(**fields)
        self._db.add(service)
        self._db.commit()
        self._db.refresh(service)
        return service

    def update_sync_fields(self, service: Service, synced_at: datetime, **fields) -> None:
        for key, value in fields.items():
            setattr(service, key, value)
        service.last_synced_at = synced_at
        self._db.commit()

    def update_admin_fields(self, service: Service, **fields) -> None:
        for key, value in fields.items():
            setattr(service, key, value)
        self._db.commit()

    def set_active(self, service: Service, is_active: bool) -> None:
        service.is_active = is_active
        self._db.commit()
