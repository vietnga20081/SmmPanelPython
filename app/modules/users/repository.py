"""Repository layer for the users module. Admin-facing queries over `users`."""
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.auth.models import User, UserRole

PAGE_SIZE = 10


class UsersRepository:
    """Search, paginate, and mutate the shared `users` table."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def search_paginated(
        self, q: str, role: str, status: str, page: int, page_size: int = PAGE_SIZE
    ) -> tuple[list[User], int]:
        stmt = select(User)
        count_stmt = select(func.count()).select_from(User)

        if q:
            like = f"%{q}%"
            condition = or_(User.username.ilike(like), User.email.ilike(like))
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)

        if role in {r.value for r in UserRole}:
            stmt = stmt.where(User.role == UserRole(role))
            count_stmt = count_stmt.where(User.role == UserRole(role))

        if status == "active":
            stmt = stmt.where(User.is_active.is_(True))
            count_stmt = count_stmt.where(User.is_active.is_(True))
        elif status == "inactive":
            stmt = stmt.where(User.is_active.is_(False))
            count_stmt = count_stmt.where(User.is_active.is_(False))

        total = self._db.execute(count_stmt).scalar_one()
        offset = max(page - 1, 0) * page_size
        stmt = stmt.order_by(User.id.desc()).offset(offset).limit(page_size)
        items = list(self._db.execute(stmt).scalars().all())
        return items, total

    def get_by_id(self, user_id: int) -> User | None:
        return self._db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email).limit(1)
        return self._db.execute(stmt).scalar_one_or_none()

    def create(self, username: str, email: str, password_hash: str, role: UserRole) -> User:
        user = User(username=username, email=email, password_hash=password_hash, role=role)
        self._db.add(user)
        self._db.commit()
        self._db.refresh(user)
        return user

    def update_profile(self, user: User, email: str, role: UserRole, is_active: bool) -> None:
        user.email = email
        user.role = role
        user.is_active = is_active
        self._db.commit()

    def update_password(self, user: User, password_hash: str) -> None:
        user.password_hash = password_hash
        self._db.commit()

    def count_active_admins(self, exclude_user_id: int | None = None) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.role == UserRole.ADMIN, User.is_active.is_(True)
        )
        if exclude_user_id is not None:
            stmt = stmt.where(User.id != exclude_user_id)
        return self._db.execute(stmt).scalar_one()
