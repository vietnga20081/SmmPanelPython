"""Pydantic schemas for the services module."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PlatformRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    platform_id: int


class ServiceListItem(BaseModel):
    """Row shown in the services catalog table."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    provider_id: int
    provider_service_ref: str
    platform: PlatformRead | None
    category: CategoryRead | None
    provider_rate: float
    sell_price: float
    min_quantity: int
    max_quantity: int
    is_active: bool
    last_synced_at: datetime | None


class ServiceUpdateForm(BaseModel):
    """Payload for POST /admin/services/{id}/edit."""

    name: str = Field(min_length=2, max_length=300)
    platform_id: int
    category_id: int
    sell_price: float = Field(ge=0)
    is_active: bool = False


class SyncResult(BaseModel):
    """Summary returned after syncing a provider's catalog."""

    created: int
    updated: int
    failed: int
    total_from_provider: int
