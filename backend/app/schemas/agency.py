"""Public share-link DTOs (agency client graph removed)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ShareResourceType = Literal["concept", "video_project", "report", "brief", "custom"]


class ShareLinkCreateRequest(BaseModel):
    workspace_id: UUID
    resource_type: ShareResourceType = "custom"
    resource_id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    expires_at: datetime | None = None
    allow_download: bool = False
    password: str | None = Field(default=None, min_length=4, max_length=128)
    snapshot: dict[str, object] = Field(default_factory=dict)


class ShareLinkDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    resource_type: ShareResourceType
    resource_id: UUID | None = None
    title: str
    token_prefix: str
    share_url: str | None = None
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    allow_download: bool
    has_password: bool
    view_count: int
    last_viewed_at: datetime | None = None
    created_at: datetime


class ShareLinkPublicDto(BaseModel):
    title: str
    resource_type: ShareResourceType
    allow_download: bool
    snapshot: dict[str, object] = Field(default_factory=dict)
    requires_password: bool = False


class ShareLinkUnlockRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


__all__ = [
    "ShareResourceType",
    "ShareLinkCreateRequest",
    "ShareLinkDto",
    "ShareLinkPublicDto",
    "ShareLinkUnlockRequest",
]
