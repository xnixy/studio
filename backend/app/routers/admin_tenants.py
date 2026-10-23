"""Platform admin: account plan/limits, usage, audit.

Solo product: one personal workspace per user is the account billing root.
No multi-member / team controls.
"""
from __future__ import annotations

from datetime import date

from app.routers._admin_shared import *  # noqa: F403
from app.models import BillingAddOn
from app.schemas import AdminBoostDto
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

_MEDIA_LIMIT_KEYS = {
    "script_generation_limit",
    "voiceover_seconds_limit",
    "video_credit_limit",
    "image_generation_limit",
    "avatar_lipsync_limit",
    "storage_gb_limit",
}


async def map_account(session, workspace, sub, owner) -> AdminWorkspaceDto:
    overrides = dict(sub.limit_overrides or {}) if sub else {}
    effective = apply_limit_overrides(plan_for(sub.plan if sub else "free"), overrides)
    media_limits = {k: int(v) for k, v in asdict(effective).items() if k in _MEDIA_LIMIT_KEYS}
    root_id = workspace.billing_workspace_id or workspace.id
    addon_rows = (
        await session.scalars(
            select(BillingAddOn).where(
                BillingAddOn.workspace_id == root_id,
                BillingAddOn.status == "active",
            )
        )
    ).all()
    boosts = [
        AdminBoostDto(
            id=row.id,
            addon_type=row.addon_type,
            quantity=max(0, int(row.quantity or 0)),
            notes=row.notes,
            status=row.status,
            monthly_total_cents=max(0, int(row.unit_price_cents or 0)) * max(0, int(row.quantity or 0)),
        )
        for row in addon_rows
    ]
    return AdminWorkspaceDto(
        id=workspace.id,
        name=workspace.name,
        owner_email=owner.email if owner else None,
        plan=sub.plan if sub else "free",
        subscription_status=sub.status if sub else "unknown",
        created_at=workspace.created_at,
        limit_overrides={k: int(v) for k, v in overrides.items() if k in media_limits or k.endswith("_limit")},
        effective_limits=media_limits,
        boosts=boosts,
    )


async def load_row(session, workspace_id):
    workspace = await session.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if workspace is None:
        raise HTTPException(status_code=404, detail="Account not found")
    owner = await session.get(User, workspace.created_by_id)
    root_id = workspace.billing_workspace_id or workspace.id
    sub = await session.scalar(select(Subscription).where(Subscription.workspace_id == root_id))
    return workspace, sub, owner


@router.get("/workspaces", response_model=list[AdminWorkspaceDto])
async def list_accounts(
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """List personal billing roots (one per account)."""
    ids = list(
        (
            await session.scalars(
                select(Workspace.id)
                .where(Workspace.billing_workspace_id == Workspace.id)
                .order_by(Workspace.created_at.desc())
                .limit(limit)
            )
        ).all()
    )
    return [await map_account(session, *(await load_row(session, workspace_id))) for workspace_id in ids]


@router.patch("/workspaces/{workspace_id}", response_model=AdminWorkspaceDto)
async def update_account_controls(
    workspace_id: UUID,
    payload: AdminWorkspaceUpdateRequest,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    workspace, sub, owner = await load_row(session, workspace_id)
    root_id = workspace.billing_workspace_id or workspace.id
    if sub is None:
        sub = Subscription(workspace_id=root_id, plan="free", status="active")
        session.add(sub)
        await session.flush()
    before = {"plan": sub.plan, "status": sub.status, "limit_overrides": dict(sub.limit_overrides or {})}
    if payload.plan is not None:
        sub.plan = payload.plan
    if payload.subscription_status is not None:
        sub.status = payload.subscription_status
    if payload.limit_overrides is not None:
        sub.limit_overrides = dict(payload.limit_overrides)
    session.add(
        AuditEvent(
            workspace_id=workspace.id,
            actor_id=admin.id,
            action="admin.account_controls_updated",
            details={
                "before": before,
                "after": {
                    "plan": sub.plan,
                    "status": sub.status,
                    "limit_overrides": dict(sub.limit_overrides or {}),
                },
            },
        )
    )
    await session.commit()
    return await map_account(session, *(await load_row(session, workspace_id)))


@router.get("/usage", response_model=list[AdminUsageRowDto])
async def usage_summary(
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(
                UsageEvent.workspace_id,
                Workspace.name,
                UsageEvent.event_type,
                func.coalesce(func.sum(UsageEvent.quantity), 0),
            )
            .join(Workspace, Workspace.id == UsageEvent.workspace_id)
            .where(UsageEvent.status == "consumed")
            .group_by(UsageEvent.workspace_id, Workspace.name, UsageEvent.event_type)
            .order_by(func.sum(UsageEvent.quantity).desc())
            .limit(limit)
        )
    ).all()
    return [
        AdminUsageRowDto(workspace_id=w, workspace_name=n, event_type=e, total_quantity=int(t or 0))
        for w, n, e, t in rows
    ]


@router.get("/audit", response_model=AdminAuditPageDto)
async def list_audit(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    action: str | None = Query(default=None, max_length=120),
    q: str | None = Query(
        default=None,
        max_length=120,
        description="Search action, actor email, or workspace name",
    ),
    workspace_id: UUID | None = Query(default=None),
    since: date | None = Query(default=None, description="Inclusive start date (UTC calendar day)"),
    until: date | None = Query(default=None, description="Inclusive end date (UTC calendar day)"),
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Paginated platform audit log with actor + account labels."""
    from datetime import datetime, time, timezone

    from sqlalchemy.orm import aliased

    Actor = aliased(User)
    Owner = aliased(User)

    filters = []
    if workspace_id is not None:
        filters.append(AuditEvent.workspace_id == workspace_id)
    if action and action.strip():
        filters.append(AuditEvent.action.ilike(f"%{action.strip()}%"))
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            or_(
                AuditEvent.action.ilike(term),
                Actor.email.ilike(term),
                Actor.full_name.ilike(term),
                Workspace.name.ilike(term),
                Owner.email.ilike(term),
            )
        )
    if since is not None:
        filters.append(
            AuditEvent.created_at >= datetime.combine(since, time.min, tzinfo=timezone.utc)
        )
    if until is not None:
        # Inclusive end of day in UTC.
        filters.append(
            AuditEvent.created_at
            <= datetime.combine(until, time(23, 59, 59, 999999), tzinfo=timezone.utc)
        )

    base = (
        select(AuditEvent, Workspace.name, Owner.email, Actor.email, Actor.full_name)
        .outerjoin(Workspace, Workspace.id == AuditEvent.workspace_id)
        .outerjoin(Owner, Owner.id == Workspace.created_by_id)
        .outerjoin(Actor, Actor.id == AuditEvent.actor_id)
    )
    if filters:
        base = base.where(*filters)

    total = int((await session.scalar(select(func.count()).select_from(base.subquery()))) or 0)
    rows = (
        await session.execute(base.order_by(AuditEvent.created_at.desc()).offset(offset).limit(limit))
    ).all()

    items = [
        AdminAuditDto(
            id=event.id,
            workspace_id=event.workspace_id,
            workspace_name=ws_name,
            owner_email=owner_email,
            actor_id=event.actor_id,
            actor_email=actor_email,
            actor_name=actor_name,
            action=event.action,
            details=dict(event.details or {}),
            created_at=event.created_at,
        )
        for event, ws_name, owner_email, actor_email, actor_name in rows
    ]
    return AdminAuditPageDto(items=items, total=total, limit=limit, offset=offset)
