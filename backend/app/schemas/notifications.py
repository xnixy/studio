from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    type: str
    title: str
    body: str | None = None
    href: str | None = None
    entity_kind: str | None = None
    entity_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    read_at: datetime | None = None
    created_at: datetime


class NotificationUnreadCountDto(BaseModel):
    count: int


class NotificationPreferenceDto(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID | None = None
    event_type: str
    in_app: bool = True
    email: bool = True
    toast: bool = True
    updated_at: datetime


class NotificationPreferenceUpsertRequest(BaseModel):
    workspace_id: UUID | None = None
    event_type: str = Field(default="*", max_length=80)
    in_app: bool = True
    email: bool = True
    toast: bool = True

__all__ = [
    "NotificationDto",
    "NotificationUnreadCountDto",
    "NotificationPreferenceDto",
    "NotificationPreferenceUpsertRequest",
]
