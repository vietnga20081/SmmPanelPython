"""Provider Engine — abstract base class every provider plugin implements.

Providers live under app/providers/ as independent plugins (e.g. generic_smm.py).
The DB-backed `providers` module (app/modules/providers/) stores connection
config (url, api key, driver name) and uses `get_provider_driver()` to
instantiate the right plugin at call time. No provider-specific code is
hardcoded outside its own plugin file.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass


class ProviderAPIError(Exception):
    """Raised when a provider's API returns an error or an unexpected response."""


@dataclass
class ProviderBalance:
    """Result of a balance check against the provider."""

    balance: float
    currency: str


@dataclass
class ProviderOrderResult:
    """Result of placing an order with the provider."""

    provider_order_id: str


@dataclass
class ProviderStatus:
    """Normalized order status as reported by the provider."""

    status: str
    charge: float | None = None
    start_count: int | None = None
    remains: int | None = None
    currency: str | None = None


class BaseProvider(ABC):
    """Contract every provider plugin must implement.

    Methods raise `ProviderAPIError` on any failure (network, auth, or a
    provider-side error payload) so the calling service layer only has one
    exception type to handle regardless of which plugin is active.
    """

    def __init__(self, api_url: str, api_key: str, timeout: float = 15.0) -> None:
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    def get_balance(self) -> ProviderBalance:
        """Fetch the current account balance held with this provider."""

    @abstractmethod
    def list_services(self) -> list[dict]:
        """Fetch the provider's full service catalog (raw provider-shaped dicts)."""

    @abstractmethod
    def add_order(self, service_id: str, link: str, quantity: int, **extra: str) -> ProviderOrderResult:
        """Place an order with the provider. `extra` covers runs/interval/comments/etc."""

    @abstractmethod
    def get_status(self, provider_order_id: str) -> ProviderStatus:
        """Fetch the status of a single previously placed order."""

    @abstractmethod
    def get_multi_status(self, provider_order_ids: list[str]) -> dict[str, ProviderStatus]:
        """Fetch statuses for multiple orders in one call, keyed by provider order id."""

    @abstractmethod
    def cancel(self, provider_order_ids: list[str]) -> dict[str, str]:
        """Request cancellation for one or more orders. Returns id -> result message."""

    @abstractmethod
    def refill(self, provider_order_id: str) -> str:
        """Request a refill for an order. Returns the provider's refill id."""

    @abstractmethod
    def get_refill_status(self, refill_id: str) -> str:
        """Fetch the status of a previously requested refill."""
