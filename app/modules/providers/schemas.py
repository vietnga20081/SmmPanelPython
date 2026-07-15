"""Pydantic schemas for the providers module."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProviderListItem(BaseModel):
    """Row shown in the providers table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    driver: str
    api_url: str
    is_active: bool
    cached_balance: float | None
    cached_currency: str | None
    last_checked_at: datetime | None
    last_error: str | None


class ProviderCreateForm(BaseModel):
    """Payload for POST /admin/providers/new."""

    name: str = Field(min_length=2, max_length=100)
    driver: str
    api_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(min_length=4, max_length=255)
    markup_percent: float = Field(default=0.0, ge=0, le=1000)


class ProviderUpdateForm(BaseModel):
    """Payload for POST /admin/providers/{id}/edit."""

    name: str = Field(min_length=2, max_length=100)
    driver: str
    api_url: str = Field(min_length=8, max_length=500)
    api_key: str = Field(min_length=4, max_length=255)
    markup_percent: float = Field(default=0.0, ge=0, le=1000)
    is_active: bool = False
