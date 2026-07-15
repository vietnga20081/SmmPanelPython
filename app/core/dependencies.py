"""Shared FastAPI dependencies: current session user, role-based access control."""
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.auth.models import User, UserRole
from app.modules.auth.repository import UserRepository
from app.modules.auth.service import has_permission


def get_current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Return the logged-in user for this session, or None if not authenticated."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return UserRepository(db).get_by_id(user_id)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Return the logged-in user for this session, raising 401 if not authenticated."""
    user = get_current_user_optional(request, db)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chưa đăng nhập.")
    return user


def require_role(permission: str) -> Callable[[User], User]:
    """Build a dependency that enforces the current user holds the given permission."""

    def _checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Không đủ quyền truy cập.")
        return user

    return _checker


require_admin = require_role("admin.access")
require_staff = require_role("staff.access")
require_client = require_role("client.access")


def is_admin(role: UserRole) -> bool:
    """Convenience check used in templates via Jinja globals."""
    return role == UserRole.ADMIN
