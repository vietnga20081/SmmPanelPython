"""Business logic for managing provider accounts and testing connectivity."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.modules.providers.models import Provider
from app.modules.providers.repository import ProvidersRepository
from app.modules.providers.validators import (
    ProviderValidationFailure,
    validate_api_url,
    validate_driver,
    validate_markup_percent,
)
from app.providers.base import ProviderAPIError
from app.providers.registry import build_provider_client

audit_logger = get_logger("audit")


class ProvidersError(Exception):
    """Base class for providers-module failures."""


class DuplicateProviderNameError(ProvidersError):
    """Raised when a provider name is already in use."""


class ProvidersService:
    """Use cases for CRUD and connectivity testing of provider accounts."""

    def __init__(self, db: Session) -> None:
        self._repo = ProvidersRepository(db)

    def list_providers(self) -> list[Provider]:
        return self._repo.list_all()

    def get_provider(self, provider_id: int) -> Provider | None:
        return self._repo.get_by_id(provider_id)

    def create_provider(
        self, name: str, driver: str, api_url: str, api_key: str, markup_percent: float = 0.0
    ) -> Provider:
        name = name.strip()
        driver = validate_driver(driver)
        api_url = validate_api_url(api_url)
        markup_percent = validate_markup_percent(markup_percent)
        if self._repo.get_by_name(name) is not None:
            raise DuplicateProviderNameError("Tên provider đã tồn tại.")
        provider = self._repo.create(name, driver, api_url, api_key.strip(), markup_percent)
        audit_logger.info("provider_created name=%s driver=%s markup=%s", name, driver, markup_percent)
        return provider

    def update_provider(
        self,
        provider_id: int,
        name: str,
        driver: str,
        api_url: str,
        api_key: str,
        markup_percent: float,
        is_active: bool,
    ) -> Provider:
        provider = self._repo.get_by_id(provider_id)
        if provider is None:
            raise ProvidersError("Không tìm thấy provider.")
        name = name.strip()
        driver = validate_driver(driver)
        api_url = validate_api_url(api_url)
        markup_percent = validate_markup_percent(markup_percent)
        existing = self._repo.get_by_name(name)
        if existing is not None and existing.id != provider.id:
            raise DuplicateProviderNameError("Tên provider đã tồn tại.")
        self._repo.update(provider, name, driver, api_url, api_key.strip(), markup_percent, is_active)
        audit_logger.info("provider_updated id=%s name=%s markup=%s", provider.id, name, markup_percent)
        return provider

    def delete_provider(self, provider_id: int) -> None:
        provider = self._repo.get_by_id(provider_id)
        if provider is None:
            raise ProvidersError("Không tìm thấy provider.")
        self._repo.delete(provider)
        audit_logger.info("provider_deleted id=%s name=%s", provider_id, provider.name)

    def toggle_active(self, provider_id: int) -> Provider:
        provider = self._repo.get_by_id(provider_id)
        if provider is None:
            raise ProvidersError("Không tìm thấy provider.")
        self._repo.set_toggle_active(provider, not provider.is_active)
        return provider

    def test_connection(self, provider_id: int) -> tuple[bool, str]:
        """Call the provider's `balance` endpoint and cache the result.

        Returns (success, message).
        """
        provider = self._repo.get_by_id(provider_id)
        if provider is None:
            raise ProvidersError("Không tìm thấy provider.")

        checked_at = datetime.now(timezone.utc)
        try:
            client = build_provider_client(provider.driver, provider.api_url, provider.api_key)
            result = client.get_balance()
        except (ProviderAPIError, ProviderValidationFailure) as exc:
            message = str(exc)
            self._repo.save_test_result(provider, None, None, message, checked_at)
            audit_logger.warning("provider_test_failed id=%s error=%s", provider.id, message)
            return False, message
        except Exception:  # noqa: BLE001 — surface any unexpected plugin/network failure safely
            message = "Kết nối thất bại: kiểm tra lại API URL / API key."
            self._repo.save_test_result(provider, None, None, message, checked_at)
            audit_logger.warning("provider_test_failed id=%s error=unexpected", provider.id)
            return False, message

        self._repo.save_test_result(provider, result.balance, result.currency, None, checked_at)
        audit_logger.info("provider_test_ok id=%s balance=%s", provider.id, result.balance)
        return True, f"Kết nối OK. Số dư: {result.balance:,.2f} {result.currency}"
