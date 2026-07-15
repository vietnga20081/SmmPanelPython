"""Provider driver registry. Maps a stored `driver` string to its plugin class.

Adding a new provider TYPE (not just a new provider account) means adding a
new file under app/providers/ implementing BaseProvider, then registering it
here. No other code needs to change.
"""
from app.providers.base import BaseProvider
from app.providers.generic_smm import GenericSMMv2Provider

PROVIDER_DRIVERS: dict[str, type[BaseProvider]] = {
    "generic_smm_v2": GenericSMMv2Provider,
}

DRIVER_LABELS: dict[str, str] = {
    "generic_smm_v2": "Chuẩn SMM Panel API v2 (key/action) — KingSmm, PerfectPanel, ...",
}


def get_provider_driver(driver: str) -> type[BaseProvider]:
    """Look up the plugin class for a stored driver key. Raises KeyError if unknown."""
    return PROVIDER_DRIVERS[driver]


def build_provider_client(driver: str, api_url: str, api_key: str) -> BaseProvider:
    """Instantiate the correct plugin for a Provider DB row."""
    driver_cls = get_provider_driver(driver)
    return driver_cls(api_url=api_url, api_key=api_key)
