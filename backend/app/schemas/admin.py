from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import AppEmail, ContactTopic, PlanName, Role

class AdminUserDto(BaseModel):
    id: UUID
    email: AppEmail
    created_at: datetime
    role: Role
    permissions: dict[str, bool]
    full_name: str | None = None
    is_disabled: bool = False
    last_login_at: datetime | None = None
    workspace_count: int = 0


class AdminUserUpdateRequest(BaseModel):
    role: Role | None = None
    is_disabled: bool | None = None
    full_name: str | None = Field(default=None, max_length=100)

    permissions: dict[str, bool] | None = None


class AdminContactDto(BaseModel):
    id: UUID
    name: str
    email: AppEmail
    topic: ContactTopic
    message: str
    created_at: datetime
    resolved_at: datetime | None = None


class AdminOverviewDto(BaseModel):
    users: int
    admins: int
    disabled_users: int
    workspaces: int
    contacts_open: int
    contacts_total: int
    jobs_queued: int
    jobs_running: int
    jobs_failed: int
    renders_queued: int
    renders_running: int
    subscriptions_by_plan: dict[str, int]
    maintenance_enabled: bool
    stripe_configured: bool
    redis_healthy: bool
    ffmpeg_available: bool
    r2_enabled: bool
    xai_configured: bool


class AdminWorkspaceUpdateRequest(BaseModel):
    """Plan / meter overrides for a personal account (billing root)."""

    plan: PlanName | None = None
    subscription_status: Literal["active", "trialing", "past_due", "unpaid", "paused", "canceled"] | None = None
    limit_overrides: dict[str, int] | None = None

    @field_validator("limit_overrides")
    @classmethod
    def validate_limit_overrides(cls, value: dict[str, int] | None) -> dict[str, int] | None:
        if value is None:
            return value
        allowed = {
            "script_generation_limit",
            "voiceover_seconds_limit",
            "video_credit_limit",
            "image_generation_limit",
            "avatar_lipsync_limit",
            "storage_gb_limit",
            "clone_slot_limit",
        }
        if unknown := set(value) - allowed:
            raise ValueError(f"Unknown limit override(s): {', '.join(sorted(unknown))}")
        if any(int(item) < 0 for item in value.values()):
            raise ValueError("Limit overrides must be zero or greater")
        return {key: int(item) for key, item in value.items()}


class AdminBoostDto(BaseModel):
    """Active recurring monthly boost on an account."""

    id: UUID
    addon_type: str
    quantity: int
    notes: str | None = None
    status: str
    monthly_total_cents: int = 0


class AdminWorkspaceDto(BaseModel):
    """One personal account (internal workspace id = billing root)."""

    id: UUID
    name: str
    owner_email: str | None = None
    plan: str
    subscription_status: str
    created_at: datetime
    limit_overrides: dict[str, int] = Field(default_factory=dict)
    effective_limits: dict[str, int] = Field(default_factory=dict)
    boosts: list[AdminBoostDto] = Field(default_factory=list)


class AdminJobDto(BaseModel):
    id: UUID
    workspace_id: UUID
    job_type: str
    status: str
    attempts: int
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AdminJobStatsDto(BaseModel):
    queued: int
    running: int
    failed: int
    completed: int
    canceled: int


class AdminUsageRowDto(BaseModel):
    workspace_id: UUID
    workspace_name: str
    event_type: str
    total_quantity: int


class AdminAuditDto(BaseModel):
    id: UUID
    workspace_id: UUID
    workspace_name: str | None = None
    owner_email: AppEmail | None = None
    actor_id: UUID | None = None
    actor_email: AppEmail | None = None
    actor_name: str | None = None
    action: str
    details: dict
    created_at: datetime


class AdminAuditPageDto(BaseModel):
    items: list[AdminAuditDto]
    total: int
    limit: int
    offset: int


__all__ = [
    "AdminUserDto",
    "AdminUserUpdateRequest",
    "AdminContactDto",
    "AdminOverviewDto",
    "AdminWorkspaceUpdateRequest",
    "AdminBoostDto",
    "AdminWorkspaceDto",
    "AdminJobDto",
    "AdminJobStatsDto",
    "AdminUsageRowDto",
    "AdminAuditDto",
    "AdminAuditPageDto",
]
