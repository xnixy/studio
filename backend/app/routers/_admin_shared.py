"""Platform operator console APIs (User.role == admin)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_admin_user
from app.job_queue import cancel_job
from app.models import (
    AuditEvent,
    BackgroundJob,
    ContactMessage,
    MaintenanceSetting,
    RefreshToken,
    Subscription,
    UsageEvent,
    User,
    VideoRender,
    Workspace,
    WorkspaceMember,
)
from app.plans import apply_limit_overrides, plan_for
from app.schemas import (
    AdminAuditDto,
    AdminAuditPageDto,
    AdminContactDto,
    AdminJobDto,
    AdminJobStatsDto,
    AdminOverviewDto,
    AdminUsageRowDto,
    AdminUserDto,
    AdminUserUpdateRequest,
    AdminWorkspaceDto,
    AdminWorkspaceUpdateRequest,
    MaintenanceStatus,
    MaintenanceUpdateRequest,
    MessageResponse,
)
from app.video_renderer import ffmpeg_path


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def map_admin_user(user: User, workspace_count: int = 0) -> AdminUserDto:
    return AdminUserDto(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        role=user.role,  # type: ignore[arg-type]
        permissions=user.permissions or {},
        full_name=user.full_name,
        is_disabled=bool(getattr(user, "is_disabled", False)),
        last_login_at=getattr(user, "last_login_at", None),
        workspace_count=workspace_count,
    )



