from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.email_delivery import EmailDeliveryError, send_email
from app.models import (
    AuditEvent,
    StripeEvent,
    Subscription,
    UsageEvent,
    User,
    Workspace,
    WorkspaceMember,
)
from app.plans import PLAN_CATALOG, plan_for
from app.schemas import (
    BillingSessionDto,
    BillingStatusDto,
    CheckoutRequest,
    MessageResponse,
    PlanDto,
    UsageEventDto,
    WorkspaceDto,
    WorkspaceMemberDto,
)
from app.stripe_billing import (
    StripeBillingError,
    construct_webhook_event,
    create_checkout_session,
    create_portal_session,
)
from app.workspace_access import (
    ROLE_PERMISSIONS,
    billing_workspace,
    ensure_personal_workspace,
    get_membership,
    get_subscription,
    month_start,
    require_permission,
    reserve_usage_committed,
    usage_total,
)



def plan_dto(name: str) -> PlanDto:
    from app.plans import clip_credit_limit

    plan = plan_for(name)
    data = dict(plan.__dict__)
    data["play_clip_limit"] = clip_credit_limit(plan)
    return PlanDto(**data)


def next_month(value: datetime) -> datetime:
    return value.replace(year=value.year + (1 if value.month == 12 else 0), month=1 if value.month == 12 else value.month + 1)


async def billing_payload(session: AsyncSession, workspace_id: UUID, settings: Settings) -> BillingStatusDto:
    """Shared billing status DTO for /billing and any route that needs plan usage."""
    from app.plan_entitlements import entitlements_public
    from app.plan_features import plan_product_mode
    from app.schemas.billing import PlanEntitlementsDto
    from app.workspace_access import effective_limits

    from app.workspace_access import effective_plan_name

    root = await billing_workspace(session, workspace_id)
    subscription = await get_subscription(session, workspace_id)
    limits = await effective_limits(session, workspace_id)
    plan_name = effective_plan_name(subscription)
    mode = plan_product_mode(plan_name)
    ent = entitlements_public(plan_name)
    scripts = await usage_total(session, workspace_id, "script_generation")
    voice = await usage_total(session, workspace_id, "voiceover_seconds")
    images = await usage_total(session, workspace_id, "image_generation")
    play_clip = await usage_total(session, workspace_id, "play_avatar")
    play_still = await usage_total(session, workspace_id, "play_still")
    play_face = await usage_total(session, workspace_id, "play_face")
    from app.plans import clip_credit_limit

    clip_limit = clip_credit_limit(limits)
    clip_remaining = max(0, clip_limit - play_clip)
    start = subscription.current_period_start or month_start()
    end = subscription.current_period_end or next_month(start)
    return BillingStatusDto(
        workspace_id=workspace_id,
        billing_workspace_id=root.id,
        plan=limits.name,  # type: ignore[arg-type]
        status=subscription.status,
        stripe_configured=bool(settings.stripe_secret_key and settings.stripe_price_ids),
        plans=[plan_dto(item.name) for item in PLAN_CATALOG],
        plan_track=mode.track,  # type: ignore[arg-type]
        features=sorted(mode.features),
        suggested_upgrade=mode.suggested_upgrade,  # type: ignore[arg-type]
        entitlements=PlanEntitlementsDto(**ent),
        script_generations_used=scripts,
        script_generations_remaining=max(0, limits.script_generation_limit - scripts),
        voiceover_seconds_used=voice,
        voiceover_seconds_remaining=max(0, limits.voiceover_seconds_limit - voice),
        # Legacy fields = max of function remainings for older UI
        image_generations_used=max(images, play_still),
        image_generations_remaining=max(0, limits.play_still_limit - play_still),
        video_generations_used=play_clip,
        video_generations_remaining=clip_remaining,
        avatar_lipsyncs_used=0,
        avatar_lipsyncs_remaining=0,
        play_video_used=play_clip,
        play_video_remaining=clip_remaining,
        play_avatar_used=play_clip,
        play_avatar_remaining=clip_remaining,
        play_clip_used=play_clip,
        play_clip_remaining=clip_remaining,
        play_still_used=play_still,
        play_still_remaining=max(0, limits.play_still_limit - play_still),
        play_face_used=play_face,
        play_face_remaining=max(0, limits.play_face_limit - play_face),
        play_lipsync_used=0,
        play_lipsync_remaining=0,
        period_start=start,
        period_end=end,
        cancel_at_period_end=subscription.cancel_at_period_end,
    )


def week_start(value: datetime | None = None) -> datetime:
    now = value or datetime.now(timezone.utc)
    monday = now - timedelta(days=now.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def map_workspace(workspace: Workspace, membership: WorkspaceMember) -> WorkspaceDto:
    return WorkspaceDto(
        id=workspace.id,
        name=workspace.name,
        type=workspace.type,  # type: ignore[arg-type]
        role=membership.role,  # type: ignore[arg-type]
        member_count=len(workspace.members),
        billing_workspace_id=workspace.billing_workspace_id,
        permissions=sorted(ROLE_PERMISSIONS.get(membership.role, set())),
        created_at=workspace.created_at,
    )


def map_member(member: WorkspaceMember) -> WorkspaceMemberDto:
    return WorkspaceMemberDto(
        id=member.id,
        user_id=member.user_id,
        email=member.user.email,
        role=member.role,  # type: ignore[arg-type]
        status="active",
        email_sent=None,
        email_message=None,
        created_at=member.created_at,
    )


async def audit(session: AsyncSession, workspace_id: UUID, actor_id: UUID | None, action: str, **details: object) -> None:
    session.add(AuditEvent(workspace_id=workspace_id, actor_id=actor_id, action=action, details=details))


async def competitor_for_user(session: AsyncSession, competitor_id: UUID, user: User, permission: str) -> Competitor:
    """Load a competitor scoped to a workspace the user can access with the given permission."""
    competitor = await session.scalar(
        select(Competitor).options(selectinload(Competitor.observations)).where(Competitor.id == competitor_id)
    )
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")
    await require_permission(session, competitor.workspace_id, user, permission)
    return competitor



