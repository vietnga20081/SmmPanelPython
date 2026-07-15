"""Pydantic schemas for dashboard read models."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.auth.models import UserRole


class RecentUserItem(BaseModel):
    """Row shown in the admin/staff 'recent registrations' widget."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    is_active: bool
    created_at: datetime


class AdminDashboardStats(BaseModel):
    """System-wide overview shown to admin and staff."""

    total_users: int
    total_admins: int
    total_staff: int
    total_clients: int
    active_users: int
    inactive_users: int
    new_users_last_7_days: int
    recent_users: list[RecentUserItem]


class ClientDashboardStats(BaseModel):
    """Personal overview shown to a client."""

    username: str
    email: str
    balance: float
    role: UserRole
    is_active: bool
    member_since: datetime
