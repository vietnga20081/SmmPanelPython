"""Business logic: sync from providers, classify, and manage the sell catalog."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.modules.providers.repository import ProvidersRepository
from app.modules.services.classifier import DEFAULT_CATEGORY, DEFAULT_PLATFORM, classify_category, classify_platform
from app.modules.services.models import Service
from app.modules.services.repository import CategoryRepository, PlatformRepository, ServiceRepository
from app.modules.services.schemas import SyncResult
from app.modules.services.validators import validate_sell_price
from app.providers.base import ProviderAPIError
from app.providers.registry import build_provider_client

audit_logger = get_logger("audit")


class ServicesError(Exception):
    """Base class for services-module failures."""


def _safe_float(value: object) -> float:
    try:
        return float(value) if value not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: object) -> int:
    try:
        return int(float(value)) if value not in (None, "") else 0
    except (TypeError, ValueError):
        return 0


def _apply_markup(provider_rate: float, markup_percent: float) -> float:
    """sell_price = provider_rate * (1 + markup% / 100), rounded to whole currency units."""
    return round(provider_rate * (1 + markup_percent / 100), 2)


class ServicesService:
    """Use cases for syncing, browsing, and editing the service catalog."""

    def __init__(self, db: Session) -> None:
        self._platforms_repo = PlatformRepository(db)
        self._categories_repo = CategoryRepository(db)
        self._services_repo = ServiceRepository(db)
        self._providers_repo = ProvidersRepository(db)

    def list_platforms(self):
        return self._platforms_repo.list_all()

    def list_categories(self, platform_id: int):
        return self._categories_repo.list_by_platform(platform_id)

    def list_all_categories(self):
        return self._categories_repo.list_all()

    def list_services(self, q: str, platform_id: int | None, category_id: int | None, provider_id: int | None,
                       status: str, page: int):
        items, total = self._services_repo.search_paginated(q, platform_id, category_id, provider_id, status, page)
        return items, total

    def get_service(self, service_id: int) -> Service | None:
        return self._services_repo.get_by_id(service_id)

    def get_stats(self) -> dict:
        return {
            "total": self._services_repo.count_total(),
            "active": self._services_repo.count_active(),
            "by_platform": self._services_repo.count_by_platform()[:6],
        }

    def sync_provider(self, provider_id: int) -> SyncResult:
        """Pull the full catalog from a provider and upsert it, classified."""
        provider = self._providers_repo.get_by_id(provider_id)
        if provider is None:
            raise ServicesError("Không tìm thấy provider.")

        try:
            client = build_provider_client(provider.driver, provider.api_url, provider.api_key)
            raw_items = client.list_services()
        except (ProviderAPIError, KeyError) as exc:
            raise ServicesError(f"Đồng bộ thất bại: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 — surface any unexpected plugin/network failure safely
            raise ServicesError("Đồng bộ thất bại: không thể kết nối tới provider.") from exc

        synced_at = datetime.now(timezone.utc)
        created = updated = failed = 0

        for item in raw_items:
            try:
                was_created = self._upsert_one(provider, item, synced_at)
            except Exception:  # noqa: BLE001 — one bad row must not abort the whole sync
                failed += 1
                continue
            if was_created:
                created += 1
            else:
                updated += 1

        audit_logger.info(
            "services_synced provider_id=%s created=%s updated=%s failed=%s",
            provider_id, created, updated, failed,
        )
        return SyncResult(created=created, updated=updated, failed=failed, total_from_provider=len(raw_items))

    def _upsert_one(self, provider, item: dict, synced_at: datetime) -> bool:
        """Create or update one Service row. Returns True if a new row was created."""
        provider_id = provider.id
        ref = str(item.get("service", "")).strip()
        if not ref:
            raise ServicesError("Thiếu service id từ provider.")

        name = str(item.get("name", "")).strip() or f"Service {ref}"
        category_raw = str(item.get("category", "")).strip()
        desc = str(item.get("desc") or item.get("description") or "").strip()
        rate = _safe_float(item.get("rate"))
        min_q = _safe_int(item.get("min"))
        max_q = _safe_int(item.get("max"))
        refill = bool(item.get("refill", False))
        cancel = bool(item.get("cancel", False))
        dripfeed = bool(item.get("dripfeed", False))

        existing = self._services_repo.get_by_provider_ref(provider_id, ref)

        if existing is not None and existing.platform_locked and existing.platform is not None:
            platform_name = existing.platform.name
        else:
            platform_name = classify_platform(category_raw, name, desc)
        platform = self._platforms_repo.get_or_create(platform_name)

        if existing is not None and existing.category_locked and existing.category is not None:
            category_name = existing.category.name
        else:
            category_name = classify_category(category_raw, name, desc)
        category = self._categories_repo.get_or_create(platform.id, category_name)

        if existing is None:
            self._services_repo.create(
                provider_id=provider_id,
                provider_service_ref=ref,
                platform_id=platform.id,
                category_id=category.id,
                name=name,
                raw_provider_name=name,
                raw_provider_category=category_raw,
                description=desc or None,
                provider_rate=rate,
                sell_price=_apply_markup(rate, provider.markup_percent),
                min_quantity=min_q,
                max_quantity=max_q,
                supports_refill=refill,
                supports_cancel=cancel,
                supports_dripfeed=dripfeed,
                is_active=False,
                last_synced_at=synced_at,
            )
            return True

        update_fields: dict = {
            "raw_provider_name": name,
            "raw_provider_category": category_raw,
            "description": desc or None,
            "provider_rate": rate,
            "min_quantity": min_q,
            "max_quantity": max_q,
            "supports_refill": refill,
            "supports_cancel": cancel,
            "supports_dripfeed": dripfeed,
        }
        if not existing.platform_locked:
            update_fields["platform_id"] = platform.id
        if not existing.category_locked:
            update_fields["category_id"] = category.id
        if not existing.price_locked:
            update_fields["sell_price"] = _apply_markup(rate, provider.markup_percent)
        self._services_repo.update_sync_fields(existing, synced_at, **update_fields)
        return False

    def update_service(
        self, service_id: int, name: str, platform_id: int, category_id: int, sell_price: float, is_active: bool
    ) -> Service:
        service = self._services_repo.get_by_id(service_id)
        if service is None:
            raise ServicesError("Không tìm thấy dịch vụ.")
        validate_sell_price(sell_price)

        fields: dict = {
            "name": name.strip() or service.raw_provider_name,
            "platform_id": platform_id,
            "category_id": category_id,
            "sell_price": sell_price,
            "is_active": is_active,
            # A manual edit is always an explicit pricing decision — lock it so the
            # next sync (which recalculates price from provider_rate * markup) won't
            # silently overwrite what the admin just set.
            "price_locked": True,
        }
        if platform_id != service.platform_id:
            fields["platform_locked"] = True
        if category_id != service.category_id:
            fields["category_locked"] = True

        self._services_repo.update_admin_fields(service, **fields)
        audit_logger.info("service_updated id=%s name=%s", service.id, fields["name"])
        return service

    def toggle_active(self, service_id: int) -> Service:
        service = self._services_repo.get_by_id(service_id)
        if service is None:
            raise ServicesError("Không tìm thấy dịch vụ.")
        self._services_repo.set_active(service, not service.is_active)
        return service

    def bulk_apply_markup(self, service_ids: list[int], markup_percent: float) -> int:
        """Recompute sell_price = provider_rate * (1 + markup%) for each service, and lock it."""
        count = 0
        for service_id in service_ids:
            service = self._services_repo.get_by_id(service_id)
            if service is None:
                continue
            new_price = _apply_markup(service.provider_rate, markup_percent)
            self._services_repo.update_admin_fields(service, sell_price=new_price, price_locked=True)
            count += 1
        audit_logger.info("services_bulk_markup count=%s markup=%s", count, markup_percent)
        return count

    def bulk_set_status(self, service_ids: list[int], is_active: bool) -> int:
        count = 0
        for service_id in service_ids:
            service = self._services_repo.get_by_id(service_id)
            if service is None:
                continue
            self._services_repo.set_active(service, is_active)
            count += 1
        audit_logger.info("services_bulk_status count=%s is_active=%s", count, is_active)
        return count

    def bulk_set_category(self, service_ids: list[int], platform_id: int, category_id: int) -> int:
        count = 0
        for service_id in service_ids:
            service = self._services_repo.get_by_id(service_id)
            if service is None:
                continue
            self._services_repo.update_admin_fields(
                service, platform_id=platform_id, category_id=category_id,
                platform_locked=True, category_locked=True,
            )
            count += 1
        audit_logger.info("services_bulk_category count=%s platform_id=%s category_id=%s",
                           count, platform_id, category_id)
        return count
