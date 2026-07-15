"""Business logic for authentication: login, rate limiting, remember-me, registration."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging_config import get_logger
from app.core.security import generate_token, hash_password, hash_token, verify_password
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import LoginAttemptRepository, RememberTokenRepository, UserRepository
from app.modules.auth.validators import ValidationFailure, validate_password_strength, validate_username

settings = get_settings()
login_logger = get_logger("login")
audit_logger = get_logger("audit")


class AuthError(Exception):
    """Base class for authentication failures."""


class AccountLockedError(AuthError):
    """Raised when an account/IP has exceeded the allowed failed login attempts."""


class InvalidCredentialsError(AuthError):
    """Raised when username/password do not match or the account is inactive."""


class UsernameTakenError(AuthError):
    """Raised when attempting to register a username that already exists."""


class AuthService:
    """Coordinates repositories to implement authentication use cases."""

    def __init__(self, db: Session) -> None:
        self._db = db
        self._users = UserRepository(db)
        self._attempts = LoginAttemptRepository(db)
        self._remember_tokens = RememberTokenRepository(db)

    def register_user(self, username: str, email: str, password: str, role: UserRole = UserRole.CLIENT) -> User:
        """Create a new user after validating uniqueness and password strength."""
        username = validate_username(username)
        validate_password_strength(password)
        if self._users.get_by_username(username) is not None:
            raise UsernameTakenError("Tên đăng nhập đã tồn tại.")
        if self._users.get_by_email(email) is not None:
            raise UsernameTakenError("Email đã được sử dụng.")
        user = self._users.create(username, email, hash_password(password), role)
        audit_logger.info("user_registered username=%s role=%s", username, role.value)
        return user

    def authenticate(self, username: str, password: str, ip_address: str) -> User:
        """Validate credentials against the database, enforcing rate limiting.

        Raises AccountLockedError or InvalidCredentialsError on failure.
        """
        recent_failures = self._attempts.count_recent_failures(
            username, ip_address, settings.login_lockout_minutes
        )
        if recent_failures >= settings.login_max_attempts:
            login_logger.warning("login_locked username=%s ip=%s", username, ip_address)
            raise AccountLockedError(
                f"Tài khoản tạm khóa do đăng nhập sai quá {settings.login_max_attempts} lần. "
                f"Vui lòng thử lại sau {settings.login_lockout_minutes} phút."
            )

        user = self._users.get_by_username(username)
        password_ok = user is not None and verify_password(password, user.password_hash)

        if not password_ok or user is None or not user.is_active:
            self._attempts.record(username, ip_address, success=False)
            login_logger.warning("login_failed username=%s ip=%s", username, ip_address)
            raise InvalidCredentialsError("Tên đăng nhập hoặc mật khẩu không đúng.")

        self._attempts.record(username, ip_address, success=True)
        login_logger.info("login_success username=%s ip=%s", username, ip_address)
        return user

    def create_remember_token(self, user_id: int) -> str:
        """Issue a new opaque remember-me token, storing only its hash."""
        raw_token = generate_token()
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.remember_max_age_seconds)
        self._remember_tokens.create(user_id, hash_token(raw_token), expires_at)
        return raw_token

    def resolve_remember_token(self, raw_token: str) -> User | None:
        """Return the user associated with a valid remember-me token, or None."""
        token = self._remember_tokens.get_valid(hash_token(raw_token))
        if token is None:
            return None
        return self._users.get_by_id(token.user_id)

    def revoke_remember_token(self, raw_token: str) -> None:
        """Invalidate a remember-me token on logout."""
        token = self._remember_tokens.get_valid(hash_token(raw_token))
        if token is not None:
            self._remember_tokens.delete(token)

    def issue_api_key(self, user: User) -> str:
        """Generate and persist a new API key for a user."""
        api_key = generate_token(24)
        self._users.set_api_key(user, api_key)
        audit_logger.info("api_key_rotated user_id=%s", user.id)
        return api_key

    def get_user(self, user_id: int) -> User | None:
        return self._users.get_by_id(user_id)


ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.ADMIN: {"admin.access", "staff.access", "client.access"},
    UserRole.STAFF: {"staff.access", "client.access"},
    UserRole.CLIENT: {"client.access"},
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Check whether a role grants the given permission string."""
    return permission in ROLE_PERMISSIONS.get(role, set())
