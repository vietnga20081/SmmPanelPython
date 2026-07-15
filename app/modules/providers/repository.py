"""Repository layer for the providers module."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.providers.models import Provider


class ProvidersRepository:
    """CRUD access for the `providers` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def list_all(self) -> list[Provider]:
        stmt = select(Provider).order_by(Provider.id.desc())
        return list(self._db.execute(stmt).scalars().all())

    def get_by_id(self, provider_id: int) -> Provider | None:
        return self._db.get(Provider, provider_id)

    def get_by_name(self, name: str) -> Provider | None:
        stmt = select(Provider).where(Provider.name == name).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def create(self, name: str, driver: str, api_url: str, api_key: str, markup_percent: float = 0.0) -> Provider:
        provider = Provider(
            name=name, driver=driver, api_url=api_url, api_key=api_key, markup_percent=markup_percent
        )
        self._db.add(provider)
        self._db.commit()
        self._db.refresh(provider)
        return provider

    def update(
        self,
        provider: Provider,
        name: str,
        driver: str,
        api_url: str,
        api_key: str,
        markup_percent: float,
        is_active: bool,
    ) -> None:
        provider.name = name
        provider.driver = driver
        provider.api_url = api_url
        provider.api_key = api_key
        provider.markup_percent = markup_percent
        provider.is_active = is_active
        self._db.commit()

    def delete(self, provider: Provider) -> None:
        self._db.delete(provider)
        self._db.commit()

    def set_toggle_active(self, provider: Provider, is_active: bool) -> None:
        provider.is_active = is_active
        self._db.commit()

    def save_test_result(
        self,
        provider: Provider,
        balance: float | None,
        currency: str | None,
        error: str | None,
        checked_at: datetime,
    ) -> None:
        provider.cached_balance = balance
        provider.cached_currency = currency
        provider.last_error = error
        provider.last_checked_at = checked_at
        self._db.commit()
