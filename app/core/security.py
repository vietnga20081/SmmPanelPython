"""Password hashing, JWT tokens, secure random tokens, and CSRF helpers."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return _pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token for API authentication."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire, "iat": datetime.now(timezone.utc)}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token, returning its payload or None."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def generate_token(num_bytes: int = 32) -> str:
    """Generate a URL-safe random token (used for remember-me tokens, API keys, etc.)."""
    return secrets.token_urlsafe(num_bytes)


def hash_token(token: str) -> str:
    """Hash an opaque token (e.g. remember-me token) for safe storage at rest."""
    return hashlib.sha256(f"{settings.secret_key}:{token}".encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generate a new CSRF token to store in the user session."""
    return secrets.token_urlsafe(32)


def verify_csrf_token(session_token: str | None, submitted_token: str | None) -> bool:
    """Constant-time comparison between the session CSRF token and the submitted one."""
    if not session_token or not submitted_token:
        return False
    return hmac.compare_digest(session_token, submitted_token)
