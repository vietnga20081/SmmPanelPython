"""Validation helpers for the providers module."""
from app.providers.registry import PROVIDER_DRIVERS


class ProviderValidationFailure(Exception):
    """Raised when provider input fails validation."""


def validate_driver(driver: str) -> str:
    """Ensure the chosen driver key is a registered plugin."""
    if driver not in PROVIDER_DRIVERS:
        raise ProviderValidationFailure(f"Driver '{driver}' không tồn tại trong hệ thống.")
    return driver


def validate_api_url(api_url: str) -> str:
    """Ensure the API URL is a well-formed absolute http(s) URL."""
    api_url = api_url.strip()
    if not (api_url.startswith("http://") or api_url.startswith("https://")):
        raise ProviderValidationFailure("API URL phải bắt đầu bằng http:// hoặc https://")
    return api_url


def validate_markup_percent(markup_percent: float) -> float:
    """Ensure the default markup % is within a sane 0-1000 range."""
    if markup_percent < 0 or markup_percent > 1000:
        raise ProviderValidationFailure("Markup phải nằm trong khoảng 0 - 1000%.")
    return markup_percent
