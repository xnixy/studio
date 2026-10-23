from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

BackgroundJobStatus = Literal["queued", "running", "waiting_for_provider", "completed", "failed", "canceled"]


class BackgroundJobDto(BaseModel):
    id: UUID
    workspace_id: UUID
    job_type: str
    status: BackgroundJobStatus
    priority: int
    payload: dict[str, object] = Field(default_factory=dict)
    result: dict[str, object] = Field(default_factory=dict)
    error_message: str | None = None
    attempts: int
    max_attempts: int
    scheduled_for: datetime
    lease_expires_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_by_id: UUID | None = None
    idempotency_key: str | None = None
    usage_event_id: UUID | None = None
    cancel_requested: bool
    created_at: datetime
    updated_at: datetime


class BackgroundJobEnqueueRequest(BaseModel):
    workspace_id: UUID
    job_type: Literal["echo"] = "echo"
    payload: dict[str, object] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0, le=1000)
    idempotency_key: str | None = Field(default=None, max_length=160)


class BackgroundJobStatsDto(BaseModel):
    workspace_id: UUID
    queued: int
    running: int
    waiting_for_provider: int
    completed: int
    failed: int
    canceled: int

__all__ = [
    "BackgroundJobStatus",
    "BackgroundJobDto",
    "BackgroundJobEnqueueRequest",
    "BackgroundJobStatsDto",
]
