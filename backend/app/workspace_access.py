from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BillingAddOn, BillingCreditGrant, Subscription, UsageEvent, User, Workspace, WorkspaceMember
from app.plan_features import plan_has_feature, raise_if_feature_missing
from app.plans import PlanLimits, apply_addons, apply_limit_grants, apply_limit_overrides, plan_for


# Permission sets for workspace roles (avatar-first product).
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "owner": {
        "workspace.manage",
        "members.manage",
        "billing.manage",
        "projects.write",
        "projects.read",
        "exports.create",
        "shares.manage",
        "shares.read",
        "addons.manage",
        "audit.read",
    },
    "admin": {
        "members.manage",
        "projects.write",
        "projects.read",
        "exports.create",
        "shares.manage",
        "shares.read",
        "addons.manage",
        "audit.read",
    },
    "editor": {
        "projects.write",
        "projects.read",
        "exports.create",
        "shares.manage",
        "shares.read",
    },
    "viewer": {
        "projects.read",
        "shares.read",
    },
}

# Map usage event_type → PlanLimits attribute name
# Media meters are **token pools**: quantity from play_pricing / model.token_cost.
USAGE_LIMIT_FIELDS: dict[str, str] = {
    "script_generation": "script_generation_limit",
    "voiceover_seconds": "voiceover_seconds_limit",
    # Legacy (still accepted)
    "image_generation": "image_generation_limit",
    "video_generation": "video_credit_limit",
    "avatar_lipsync": "avatar_lipsync_limit",
    # Per-function Play meters
    "play_video": "play_video_limit",
    "play_avatar": "play_avatar_limit",
    "play_still": "play_still_limit",
    "play_face": "play_face_limit",
    "play_lipsync": "play_lipsync_limit",
}

USAGE_LABELS: dict[str, str] = {
    "script_generation": "script generations",
    "voiceover_seconds": "voiceover seconds",
    "image_generation": "still credits",
    "video_generation": "clip credits",
    "avatar_lipsync": "clip credits",
    "play_video": "clip credits",
    "play_avatar": "clip credits",
    "play_still": "still credits",
    "play_face": "face credits",
    "play_lipsync": "clip credits",
}

# Talking and Scene share one Clip pool. Leftover Photo usage counts too.
CLIP_USAGE_EVENTS = frozenset({"play_avatar", "play_video", "play_lipsync"})
CLIP_USAGE_COUNT_TYPES = (
    "play_avatar",
    "play_video",
    "play_lipsync",
    "video_generation",
    "avatar_lipsync",
)

# Legacy events counted toward the new meter when computing remaining (cutover).
LEGACY_USAGE_ALIASES: dict[str, tuple[str, ...]] = {
    "play_still": ("image_generation",),
    "play_face": ("image_generation",),
    "play_lipsync": ("avatar_lipsync",),
}


def month_start(now: datetime | None = None) -> datetime:
    value = now or datetime.now(timezone.utc)
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def get_membership(session: AsyncSession, workspace_id: UUID, user: User) -> WorkspaceMember:
    membership = await session.scalar(
        select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id, WorkspaceMember.user_id == user.id)
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return membership


async def ensure_personal_workspace(session: AsyncSession, user: User) -> Workspace:
    existing = await session.scalar(
        select(Workspace)
        .join(WorkspaceMember)
        .where(WorkspaceMember.user_id == user.id)
        .order_by(Workspace.created_at, Workspace.id)
    )
    if existing is not None:
        return existing
    workspace_id = uuid.uuid4()
    workspace = Workspace(
        id=workspace_id,
        name="Personal",
        type="personal",
        created_by_id=user.id,
        billing_workspace_id=workspace_id,
    )
    session.add(workspace)
    session.add(WorkspaceMember(workspace_id=workspace_id, user_id=user.id, role="owner"))
    session.add(Subscription(workspace_id=workspace_id, plan="free", status="active"))
    await session.commit()
    return workspace


async def require_permission(session: AsyncSession, workspace_id: UUID, user: User, permission: str) -> WorkspaceMember:
    membership = await get_membership(session, workspace_id, user)
    permissions = set(ROLE_PERMISSIONS.get(membership.role, set()))
    for name, allowed in dict(membership.permission_overrides or {}).items():
        if allowed:
            permissions.add(name)
        else:
            permissions.discard(name)
    if permission not in permissions:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient workspace permissions")
    return membership


async def require_plan_feature(session: AsyncSession, workspace_id: UUID, feature: str) -> None:
    """Hard product gate: plan track must include this feature area."""
    subscription = await get_subscription(session, workspace_id)
    raise_if_feature_missing(subscription.plan, feature)


async def workspace_has_feature(session: AsyncSession, workspace_id: UUID, feature: str) -> bool:
    subscription = await get_subscription(session, workspace_id)
    return plan_has_feature(subscription.plan, feature)


async def billing_workspace(session: AsyncSession, workspace_id: UUID) -> Workspace:
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    root_id = workspace.billing_workspace_id or workspace.id
    root = await session.get(Workspace, root_id)
    if root is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Workspace billing account is unavailable")
    return root


async def get_subscription(session: AsyncSession, workspace_id: UUID, *, lock: bool = False) -> Subscription:
    root = await billing_workspace(session, workspace_id)
    query = select(Subscription).where(Subscription.workspace_id == root.id)
    if lock:
        query = query.with_for_update()
    subscription = await session.scalar(query)
    if subscription is None:
        subscription = Subscription(workspace_id=root.id, plan="free", status="active")
        session.add(subscription)
        await session.flush()
    return subscription


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def effective_plan_name(subscription: Subscription, *, now: datetime | None = None) -> str:
    """Plan used for meters/entitlements after period end and terminal status.

    Paid access continues until current_period_end when status is canceled
    (cancel-at-period-end). After the period, or on expired/unpaid, fall back to free
    even if the stored plan column was never rewritten (e.g. missed ASSN).
    """
    plan = (subscription.plan or "free").strip().lower() or "free"
    if plan == "free":
        return "free"
    status = (subscription.status or "active").strip().lower()
    moment = now or datetime.now(timezone.utc)
    period_end = _as_utc(subscription.current_period_end)

    if status in {"expired", "unpaid", "incomplete_expired", "revoked"}:
        return "free"
    if status == "canceled":
        if period_end is not None and period_end > moment:
            return plan
        return "free"
    # active / past_due / trialing / incomplete: still honor hard period end
    if period_end is not None and period_end < moment:
        return "free"
    return plan


async def active_addon_map(session: AsyncSession, workspace_id: UUID) -> dict[str, int]:
    """Active add-on quantities for the billing root of this workspace."""
    root = await billing_workspace(session, workspace_id)
    rows = (
        await session.scalars(
            select(BillingAddOn).where(BillingAddOn.workspace_id == root.id, BillingAddOn.status == "active")
        )
    ).all()
    return {row.addon_type: int(row.quantity) for row in rows}


async def active_credit_grant_totals(session: AsyncSession, workspace_id: UUID) -> dict[str, int]:
    """Sum one-time pack grants active for the current monthly usage period."""
    root = await billing_workspace(session, workspace_id)
    now = datetime.now(timezone.utc)
    start = month_start(now)
    rows = (
        await session.scalars(
            select(BillingCreditGrant).where(
                BillingCreditGrant.workspace_id == root.id,
                BillingCreditGrant.status == "active",
                BillingCreditGrant.period_end > now,
                BillingCreditGrant.period_start <= now,
                # Only grants purchased in the current usage month count toward this period.
                BillingCreditGrant.created_at >= start,
            )
        )
    ).all()
    totals: dict[str, int] = {}
    for row in rows:
        for key, amount in dict(row.grants or {}).items():
            totals[key] = totals.get(key, 0) + max(0, int(amount))
    return totals


async def effective_limits(session: AsyncSession, workspace_id: UUID, *, lock: bool = False) -> PlanLimits:
    """Plan + admin overrides + recurring add-ons + one-time pack grants."""
    subscription = await get_subscription(session, workspace_id, lock=lock)
    plan_name = effective_plan_name(subscription)
    base = apply_limit_overrides(plan_for(plan_name), subscription.limit_overrides)
    with_addons = apply_addons(base, await active_addon_map(session, workspace_id))
    return apply_limit_grants(with_addons, await active_credit_grant_totals(session, workspace_id))


async def usage_total(session: AsyncSession, workspace_id: UUID, event_type: str) -> int:
    """Sum reserved+consumed tokens for a meter this calendar month (UTC).

    New play_* meters also count legacy event types (image_generation, etc.)
    so existing usage still reduces remaining after cutover.

    Talking and Scene share one Clip pool: play_avatar + play_video +
    leftover video_generation, counted once.
    """
    root = await billing_workspace(session, workspace_id)
    if event_type in CLIP_USAGE_EVENTS or event_type == "video_generation":
        types = CLIP_USAGE_COUNT_TYPES
    else:
        types = (event_type, *LEGACY_USAGE_ALIASES.get(event_type, ()))
    total = await session.scalar(
        select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.workspace_id == root.id,
            UsageEvent.event_type.in_(types),
            UsageEvent.status.in_(("reserved", "consumed")),
            UsageEvent.created_at >= month_start(),
        )
    )
    return int(total or 0)


# Reserved rows older than this are treated as abandoned (process crash mid-provider call).
STALE_RESERVATION_SECONDS = 45 * 60


async def release_stale_reservations(session: AsyncSession, *, older_than_seconds: int = STALE_RESERVATION_SECONDS) -> int:
    """Release abandoned reserved usage so crashes do not permanently burn plan quota."""
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(60, older_than_seconds))
    rows = (
        await session.scalars(
            select(UsageEvent).where(
                UsageEvent.status == "reserved",
                UsageEvent.created_at < cutoff,
            )
        )
    ).all()
    for event in rows:
        event.status = "released"
        meta = dict(event.event_metadata or {})
        meta["auto_released"] = True
        meta["auto_released_reason"] = "stale_reservation"
        event.event_metadata = meta
    if rows:
        await session.flush()
    return len(rows)


def limit_for_event(limits: PlanLimits, event_type: str) -> int:
    from app.plans import clip_credit_limit

    if event_type in CLIP_USAGE_EVENTS or event_type == "video_generation":
        return clip_credit_limit(limits)
    field = USAGE_LIMIT_FIELDS.get(event_type)
    if field is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown usage event type: {event_type}",
        )
    return int(getattr(limits, field))


async def reserve_usage(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: UUID | None,
    event_type: str,
    quantity: int,
    metadata: dict[str, object] | None = None,
) -> UsageEvent:
    """Lock subscription, insert reserved UsageEvent, flush only — no commit.

    Caller owns the surrounding transaction. Use for same-tx job enqueue with
    no external I/O before commit. Never hold this lock across provider awaits.
    """
    if quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usage quantity must be positive")
    # Drop abandoned reserves first so concurrent crashes cannot brick a plan for the month.
    await release_stale_reservations(session)
    # Lock subscription row first so concurrent reserves serialize on the billing root.
    limits = await effective_limits(session, workspace_id, lock=True)
    limit = limit_for_event(limits, event_type)
    used = await usage_total(session, workspace_id, event_type)
    if used + quantity > limit:
        label = USAGE_LABELS.get(event_type, event_type.replace("_", " "))
        remaining = max(0, limit - used)
        # Concrete copy: free plans have 25 clip credits and a 10s Fast
        # clip can cost 10, so the second generate looks "broken" without numbers.
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Monthly {label} limit reached "
                f"({used}/{limit} used; this run needs {quantity}, {remaining} left). "
                f"Try a shorter clip, wait for next month, or upgrade / buy a pack."
            ),
        )
    root = await billing_workspace(session, workspace_id)
    event = UsageEvent(
        workspace_id=root.id,
        user_id=user_id,
        event_type=event_type,
        quantity=quantity,
        status="reserved",
        event_metadata=metadata or {},
    )
    session.add(event)
    await session.flush()
    return event


async def reserve_usage_committed(
    session: AsyncSession,
    workspace_id: UUID,
    user_id: UUID | None,
    event_type: str,
    quantity: int,
    metadata: dict[str, object] | None = None,
) -> UsageEvent:
    """Reserve usage and commit immediately.

    Use before long external I/O (LLM, TTS, HTTP). Never hold Subscription
    FOR UPDATE across provider latency.
    """
    event = await reserve_usage(session, workspace_id, user_id, event_type, quantity, metadata)
    await session.commit()
    return event


async def finish_usage(
    session: AsyncSession,
    event: UsageEvent,
    *,
    consumed: bool,
    commit: bool = True,
) -> None:
    """Mark reserved usage consumed or released.

    Default commits. Pass commit=False when finishing inside the same
    transaction as setting a job terminal status.
    """
    event.status = "consumed" if consumed else "released"
    if commit:
        await session.commit()
    else:
        await session.flush()
