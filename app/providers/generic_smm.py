"""Generic plugin for the widely-used "SMM Panel API v2" standard.

Protocol: single POST endpoint, form-encoded body with `key` (API key) and
`action`, everything else varies per action. This exact shape is documented
by KingSmm.vn (https://kingsmm.vn/api/v2) and shared by many other panels
(PerfectPanel-compatible). One plugin, many providers — just a different
`api_url` + `api_key` per provider row in the database.
"""
import httpx

from app.providers.base import (
    BaseProvider,
    ProviderAPIError,
    ProviderBalance,
    ProviderOrderResult,
    ProviderStatus,
)


class GenericSMMv2Provider(BaseProvider):
    """Implements: services, add, status, cancel, balance, refill, refill_status."""

    def _post(self, payload: dict[str, str]) -> dict | list:
        body = {"key": self.api_key, **payload}
        try:
            response = httpx.post(self.api_url, data=body, timeout=self.timeout)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderAPIError(f"Lỗi kết nối tới provider: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderAPIError("Provider trả về dữ liệu không phải JSON hợp lệ.") from exc

        if isinstance(data, dict) and data.get("error"):
            raise ProviderAPIError(str(data["error"]))
        return data

    def get_balance(self) -> ProviderBalance:
        data = self._post({"action": "balance"})
        if not isinstance(data, dict) or "balance" not in data:
            raise ProviderAPIError("Phản hồi balance không hợp lệ.")
        return ProviderBalance(balance=float(data["balance"]), currency=str(data.get("currency", "USD")))

    def list_services(self) -> list[dict]:
        data = self._post({"action": "services"})
        if not isinstance(data, list):
            raise ProviderAPIError("Phản hồi services không hợp lệ.")
        return data

    def add_order(self, service_id: str, link: str, quantity: int, **extra: str) -> ProviderOrderResult:
        payload = {"action": "add", "service": service_id, "link": link, "quantity": str(quantity)}
        payload.update({k: v for k, v in extra.items() if v is not None})
        data = self._post(payload)
        if not isinstance(data, dict) or "order" not in data:
            raise ProviderAPIError("Phản hồi add order không hợp lệ.")
        return ProviderOrderResult(provider_order_id=str(data["order"]))

    def get_status(self, provider_order_id: str) -> ProviderStatus:
        data = self._post({"action": "status", "order": provider_order_id})
        if not isinstance(data, dict) or "status" not in data:
            raise ProviderAPIError("Phản hồi status không hợp lệ.")
        return _parse_status(data)

    def get_multi_status(self, provider_order_ids: list[str]) -> dict[str, ProviderStatus]:
        data = self._post({"action": "status", "orders": ",".join(provider_order_ids)})
        if not isinstance(data, dict):
            raise ProviderAPIError("Phản hồi multi-status không hợp lệ.")
        result: dict[str, ProviderStatus] = {}
        for order_id, item in data.items():
            if isinstance(item, dict) and not item.get("error"):
                result[order_id] = _parse_status(item)
        return result

    def cancel(self, provider_order_ids: list[str]) -> dict[str, str]:
        data = self._post({"action": "cancel", "orders": ",".join(provider_order_ids)})
        result: dict[str, str] = {}
        if isinstance(data, list):
            for item in data:
                order_id = str(item.get("order", ""))
                cancel_info = item.get("cancel", {})
                if isinstance(cancel_info, dict) and cancel_info.get("error"):
                    result[order_id] = f"error: {cancel_info['error']}"
                else:
                    result[order_id] = "ok"
        return result

    def refill(self, provider_order_id: str) -> str:
        data = self._post({"action": "refill", "order": provider_order_id})
        if not isinstance(data, dict) or "refill" not in data:
            raise ProviderAPIError("Phản hồi refill không hợp lệ.")
        return str(data["refill"])

    def get_refill_status(self, refill_id: str) -> str:
        data = self._post({"action": "refill_status", "refill": refill_id})
        if not isinstance(data, dict) or "status" not in data:
            raise ProviderAPIError("Phản hồi refill_status không hợp lệ.")
        return str(data["status"])


def _parse_status(data: dict) -> ProviderStatus:
    def _to_float(value: object) -> float | None:
        try:
            return float(value) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    def _to_int(value: object) -> int | None:
        try:
            return int(float(value)) if value not in (None, "") else None
        except (TypeError, ValueError):
            return None

    return ProviderStatus(
        status=str(data.get("status", "Unknown")),
        charge=_to_float(data.get("charge")),
        start_count=_to_int(data.get("start_count")),
        remains=_to_int(data.get("remains")),
        currency=data.get("currency"),
    )
