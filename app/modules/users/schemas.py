"""Pydantic schemas for the users module."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.auth.models import UserRole


class UserListItem(BaseModel):
    """Row shown in the users management table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    balance: float
    is_active: bool
    created_at: datetime


class UserFilterParams(BaseModel):
    """Query params accepted by GET /admin/users."""

    q: str = ""
    role: str = ""
    status: str = ""
    page: int = Field(default=1, ge=1)


class UserCreateForm(BaseModel):
    """Payload for POST /admin/users/new."""

    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class UserUpdateForm(BaseModel):
    """Payload for POST /admin/users/{id}/edit."""

    email: EmailStr
    role: UserRole
    is_active: bool = False


class PasswordResetForm(BaseModel):
    """Payload for POST /admin/users/{id}/reset-password."""

    new_password: str = Field(min_length=8, max_length=128)
