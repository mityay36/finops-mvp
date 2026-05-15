from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.cluster import ProviderType


class ClusterBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    provider_type: ProviderType
    opencost_url: HttpUrl
    vm_url: HttpUrl
    is_active: bool = True


class ClusterCreate(ClusterBase):
    """Used by POST /clusters. Credentials are sent separately via /credentials endpoint
    to keep concerns isolated and to allow editing creds without touching cluster fields."""


class ClusterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    opencost_url: HttpUrl | None = None
    vm_url: HttpUrl | None = None
    is_active: bool | None = None
    # provider_type intentionally omitted — changing provider type is not supported
    # because credentials and TCO configs are coupled to it. Delete + recreate instead.


class ClusterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    provider_type: ProviderType
    opencost_url: str
    vm_url: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ClusterDetailedRead(ClusterRead):
    """Includes credential key names (without values) for UI display."""

    credential_keys: list[str] = []
