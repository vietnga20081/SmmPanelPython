"""Validation helpers for the services module."""


class ServiceValidationFailure(Exception):
    """Raised when service input fails validation."""


def validate_sell_price(sell_price: float) -> float:
    """Ensure the sell price is a non-negative number."""
    if sell_price < 0:
        raise ServiceValidationFailure("Giá bán không được nhỏ hơn 0.")
    return sell_price
