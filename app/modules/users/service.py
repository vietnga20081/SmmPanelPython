"""Business logic for admin-facing user management."""
import math

from sqlalchemy.orm import Session

from app.core.logging_config import get_logger
from app.core.security import hash_password
from app.modules.auth.models import User, UserRole
from app.modules.auth.validators import ValidationFailure, validate_password_strength, validate_username
from app.modules.users.repository import PAGE_SIZE, UsersRepository
from app.modules.users.schemas import UserListItem

audit_logger = get_logger("audit")


class UsersError(Exception):
    """Base class for users-module failures."""


class DuplicateUserError(UsersError):
    """Raised when username/email is already taken."""


class LastAdminGuardError(UsersError):
    """Raised when an action would leave the system with zero active admins."""


class SelfActionError(UsersError):
    """Raised when an admin tries to lock themselves out."""


class UsersService:
    """Use cases for listing, creating, and updating users."""

    def __init__(self, db: Session) -> None:
        self._repo = UsersRepository(db)

    def list_users(
        self, q: str, role: str, status: str, page: int
    ) -> tuple[list[UserListItem], int, int, int]:
        """Return (items, current_page, total_pages, total_count) for the given filters."""
        items, total = self._repo.search_paginated(q, role, status, page)
        total_pages = max(math.ceil(total / PAGE_SIZE), 1)
        page = min(page, total_pages)
        return [UserListItem.model_validate(u) for u in items], page, total_pages, total

    def get_user(self, user_id: int) -> User | None:
        return self._repo.get_by_id(user_id)

    def create_user(self, username: str, email: str, password: str, role: UserRole) -> User:
        username = validate_username(username)
        validate_password_strength(password)
        if self._repo.get_by_username(username) is not None:
            raise DuplicateUserError("Tên đăng nhập đã tồn tại.")
        if self._repo.get_by_email(email) is not None:
            raise DuplicateUserError("Email đã được sử dụng.")
        user = self._repo.create(username, email, hash_password(password), role)
        audit_logger.info("user_created_by_admin id=%s username=%s role=%s", user.id, username, role.value)
        return user

    def update_user(
        self, actor: User, target_id: int, email: str, role: UserRole, is_active: bool
    ) -> User:
        """Update a user's email/role/active status, with self-lockout guards."""
        target = self._repo.get_by_id(target_id)
        if target is None:
            raise UsersError("Không tìm thấy người dùng.")

        existing_email_owner = self._repo.get_by_email(email)
        if existing_email_owner is not None and existing_email_owner.id != target.id:
            raise DuplicateUserError("Email đã được sử dụng bởi tài khoản khác.")

        is_self = actor.id == target.id
        losing_admin = target.role == UserRole.ADMIN and (role != UserRole.ADMIN or not is_active)

        if is_self and losing_admin:
            raise SelfActionError("Bạn không thể tự bỏ quyền admin hoặc tự vô hiệu hóa tài khoản của mình.")

        if losing_admin and self._repo.count_active_admins(exclude_user_id=target.id) == 0:
            raise LastAdminGuardError("Hệ thống phải còn ít nhất một admin đang hoạt động.")

        self._repo.update_profile(target, email, role, is_active)
        audit_logger.info(
            "user_updated_by_admin actor_id=%s target_id=%s role=%s active=%s",
            actor.id, target.id, role.value, is_active,
        )
        return target

    def reset_password(self, target_id: int, new_password: str) -> None:
        target = self._repo.get_by_id(target_id)
        if target is None:
            raise UsersError("Không tìm thấy người dùng.")
        validate_password_strength(new_password)
        self._repo.update_password(target, hash_password(new_password))
        audit_logger.info("user_password_reset_by_admin target_id=%s", target.id)

    def toggle_active(self, actor: User, target_id: int) -> User:
        """Flip is_active, reusing the same self-lockout / last-admin guards."""
        target = self._repo.get_by_id(target_id)
        if target is None:
            raise UsersError("Không tìm thấy người dùng.")
        return self.update_user(
            actor, target_id, email=target.email, role=target.role, is_active=not target.is_active
        )
