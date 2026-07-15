"""Repository layer for the auth module. The only layer allowed to query the DB."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import LoginAttempt, RememberToken, User, UserRole


class UserRepository:
    """Data access for the users table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_api_key(self, api_key: str) -> User | None:
        stmt = select(User).where(User.api_key == api_key).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def create(self, username: str, email: str, password_hash: str, role: UserRole) -> User:
        user = User(username=username, email=email, password_hash=password_hash, role=role)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self._db.commit()

    def set_api_key(self, user: User, api_key: str) -> None:
        user.api_key = api_key
        self._db.commit()

    def list_paginated(self, page: int, page_size: int) -> tuple[list[User], int]:
        offset = max(page - 1, 0) * page_size
        items_stmt = select(User).order_by(User.id.desc()).offset(offset).limit(page_size)
        items = list(self._db.execute(items_stmt).scalars().all())
        total = self._db.execute(select(func.count()).select_from(User)).scalar_one()
        return items, total


class LoginAttemptRepository:
    """Data access for tracking and rate-limiting login attempts."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def record(self, username: str, ip_address: str, success: bool) -> None:
        attempt = LoginAttempt(username=username, ip_address=ip_address, success=success)
        self._db.add(attempt)
        self._db.commit()

    def count_recent_failures(self, username: str, ip_address: str, window_minutes: int) -> int:
        since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
        stmt = select(func.count()).select_from(LoginAttempt).where(
            LoginAttempt.username == username,
            LoginAttempt.ip_address == ip_address,
            LoginAttempt.success.is_(False),
            LoginAttempt.created_at >= since,
        )
        return self._db.execute(stmt).scalar_one()


class RememberTokenRepository:
    """Data access for persistent 'remember me' login tokens."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def create(self, user_id: int, token_hash: str, expires_at: datetime) -> RememberToken:
        token = RememberToken(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
        self._db.add(token)
        self._db.commit()
        self._db.refresh(token)
        return token

    def get_valid(self, token_hash: str) -> RememberToken | None:
        stmt = select(RememberToken).where(
            RememberToken.token_hash == token_hash,
            RememberToken.expires_at >= datetime.now(timezone.utc),
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def delete(self, token: RememberToken) -> None:
        self._db.delete(token)
        self._db.commit()

    def delete_expired(self) -> int:
        stmt = select(RememberToken).where(RememberToken.expires_at < datetime.now(timezone.utc))
        expired = list(self._db.execute(stmt).scalars().all())
        for token in expired:
            self._db.delete(token)
        self._db.commit()
        return len(expired)
