"""Repository layer for the dashboard module. Read-only aggregate queries."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole


class DashboardRepository:
    """Aggregate, read-only queries over shared entities (currently: users)."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def count_users_by_role(self, role: UserRole) -> int:
        stmt = select(func.count()).select_from(User).where(User.role == role)
        return self._db.execute(stmt).scalar_one()

    def count_total_users(self) -> int:
        return self._db.execute(select(func.count()).select_from(User)).scalar_one()

    def count_active_users(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.is_active.is_(True))
        return self._db.execute(stmt).scalar_one()

    def count_new_users_since(self, since: datetime) -> int:
        stmt = select(func.count()).select_from(User).where(User.created_at >= since)
        return self._db.execute(stmt).scalar_one()

    def get_recent_users(self, limit: int = 8) -> list[User]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit)
        return list(self._db.execute(stmt).scalars().all())


def seven_days_ago() -> datetime:
    """Helper: UTC timestamp for 'now minus 7 days', used by new-user counts."""
    return datetime.now(timezone.utc) - timedelta(days=7)
