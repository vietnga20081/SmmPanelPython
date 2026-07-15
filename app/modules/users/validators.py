"""Validation helpers for the users module (query params, cross-field checks)."""
from app.modules.auth.models import UserRole

VALID_ROLE_FILTERS = {r.value for r in UserRole}
VALID_STATUS_FILTERS = {"active", "inactive"}


def sanitize_role_filter(role: str) -> str:
    """Return `role` if it's a recognized role value, else empty string (= no filter)."""
    return role if role in VALID_ROLE_FILTERS else ""


def sanitize_status_filter(status: str) -> str:
    """Return `status` if it's 'active'/'inactive', else empty string (= no filter)."""
    return status if status in VALID_STATUS_FILTERS else ""
