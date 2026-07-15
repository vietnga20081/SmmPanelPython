"""Pydantic schemas (input/output DTOs) for the auth module."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.modules.auth.models import UserRole


class LoginRequest(BaseModel):
    """Payload for POST /login."""

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    remember_me: bool = False


class UserCreate(BaseModel):
    """Payload for creating a new user (admin/staff/client)."""

    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CLIENT


class UserRead(BaseModel):
    """Public representation of a user."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    role: UserRole
    balance: float
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """JWT access token response for the REST API."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
