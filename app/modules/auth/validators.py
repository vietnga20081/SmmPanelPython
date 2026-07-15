"""Input validation helpers for the auth module, beyond basic Pydantic types."""
import re

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.-]{3,50}$")
_PASSWORD_MIN_LEN = 8


class ValidationFailure(Exception):
    """Raised when user-supplied auth data fails validation."""


def validate_username(username: str) -> str:
    """Validate and normalize a username. Raises ValidationFailure on error."""
    username = username.strip()
    if not _USERNAME_RE.match(username):
        raise ValidationFailure(
            "Username phải từ 3-50 ký tự, chỉ gồm chữ, số, dấu chấm, gạch dưới hoặc gạch ngang."
        )
    return username


def validate_password_strength(password: str) -> None:
    """Enforce minimum password strength. Raises ValidationFailure on error."""
    if len(password) < _PASSWORD_MIN_LEN:
        raise ValidationFailure(f"Mật khẩu phải có ít nhất {_PASSWORD_MIN_LEN} ký tự.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"[0-9]", password):
        raise ValidationFailure("Mật khẩu phải chứa cả chữ và số.")


def validate_role(role: str, allowed_roles: set[str]) -> None:
    """Ensure a role string is one of the roles allowed in the current context."""
    if role not in allowed_roles:
        raise ValidationFailure(f"Vai trò '{role}' không hợp lệ.")
