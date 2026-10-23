"""Billing add-ons and effective limits.

User-facing add-on rows are read-only / cancel-only. Granting extra limits is
admin-only (or via paid packs / Stripe plans). Free self-service upsert was removed.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.credit_packs import map_credit_grant, pack_dtos
from app.database import get_session
from app.dependencies import get_admin_user, get_current_user
from app.models import AuditEvent, BillingAddOn, BillingCreditGrant, User
from app.plans import ADDON_UNIT_PRICES_CENTS
from app.schemas import (
    BillingAddOnDto,
    BillingAddOnUpsertRequest,
    EffectiveLimitsDto,
    MessageResponse,
)
from app.workspace_access import billing_workspace, effective_limits, get_subscription, month_start, require_permission

router = APIRouter(tags=["billing"])

# Soft cap when admins grant boosts (prevents accidental 10k abuse in admin UI too).
_ADMIN_ADDON_QTY_MAX = 500


def map_addon(addon: BillingAddOn) -> BillingAddOnDto:
    qty = max(0, int(addon.quantity or 0))
    unit = max(0, int(addon.unit_price_cents or 0))
    return BillingAddOnDto(
        id=addon.id,
        workspace_id=addon.workspace_id,
        addon_type=addon.addon_type,  # type: ignore[arg-type]
        quantity=qty,
        unit_price_cents=unit,
        status=addon.status,  # type: ignore[arg-type]
        notes=addon.notes,
        monthly_total_cents=unit * qty,
        created_at=addon.created_at,
        updated_at=addon.updated_at,
    )


@router.get("/billing/addons", response_model=EffectiveLimitsDto)
async def get_effective_limits(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> EffectiveLimitsDto:
    await require_permission(session, workspace_id, user, "projects.read")
    root = await billing_workspace(session, workspace_id)

    subscription = await get_subscription(session, root.id)
    addons = (
        await session.scalars(
            select(BillingAddOn).where(BillingAddOn.workspace_id == root.id, BillingAddOn.status == "active")
        )
    ).all()
    effective = await effective_limits(session, root.id)
    grants = (
        await session.scalars(
            select(BillingCreditGrant)
            .where(
                BillingCreditGrant.workspace_id == root.id,
                BillingCreditGrant.status == "active",
                BillingCreditGrant.created_at >= month_start(),
            )
            .order_by(BillingCreditGrant.created_at.desc())
            .limit(20)
        )
    ).all()
    settings = get_settings()
    return EffectiveLimitsDto(
        plan=subscription.plan,  # type: ignore[arg-type]
        seat_limit=effective.seat_limit,
        video_credit_limit=effective.video_credit_limit,
        image_generation_limit=effective.image_generation_limit,
        avatar_lipsync_limit=effective.avatar_lipsync_limit,
        storage_gb_limit=effective.storage_gb_limit,
        priority_rendering=effective.priority_rendering,
        script_generation_limit=effective.script_generation_limit,
        voiceover_seconds_limit=effective.voiceover_seconds_limit,
        addons=[map_addon(addon) for addon in addons],
        credit_grants=[map_credit_grant(g) for g in grants],
        packs=pack_dtos(settings),
    )


@router.put("/billing/addons", response_model=BillingAddOnDto)
async def upsert_addon_user_blocked(
    payload: BillingAddOnUpsertRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BillingAddOnDto:
    """Public upsert is closed: free self-service boosts were a billing abuse path.

    Buy credit packs or upgrade the plan. Platform admins use PUT /admin/billing/addons.
    """
    await require_permission(session, payload.workspace_id, user, "addons.manage")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "Monthly boosts cannot be activated from the app without payment. "
            "Buy a credit pack or upgrade your plan for more tokens."
        ),
    )


@router.delete("/billing/addons/{addon_type}", response_model=MessageResponse)
async def cancel_addon(
    addon_type: str,
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    await require_permission(session, workspace_id, user, "addons.manage")
    root = await billing_workspace(session, workspace_id)
    cleaned = (addon_type or "").strip()
    if cleaned not in ADDON_UNIT_PRICES_CENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown add-on type")
    existing = await session.scalar(
        select(BillingAddOn).where(
            BillingAddOn.workspace_id == root.id,
            BillingAddOn.addon_type == cleaned,
            BillingAddOn.status == "active",
        )
    )
    if existing is None:
        return MessageResponse(message="Add-on already inactive")
    existing.status = "canceled"
    existing.updated_at = datetime.now(timezone.utc)
    session.add(
        AuditEvent(
            workspace_id=root.id,
            actor_id=user.id,
            action="addon.canceled",
            details={"addon_type": cleaned},
        )
    )
    await session.commit()
    return MessageResponse(message="Add-on cancelled")


@router.put("/admin/billing/addons", response_model=BillingAddOnDto)
async def admin_upsert_addon(
    payload: BillingAddOnUpsertRequest,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> BillingAddOnDto:
    """Platform admin only: grant or adjust a recurring boost (support / ops)."""
    if payload.quantity > _ADMIN_ADDON_QTY_MAX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantity must be at most {_ADMIN_ADDON_QTY_MAX}",
        )
    if payload.addon_type not in ADDON_UNIT_PRICES_CENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown add-on type")
    root = await billing_workspace(session, payload.workspace_id)
    existing = await session.scalar(
        select(BillingAddOn).where(BillingAddOn.workspace_id == root.id, BillingAddOn.addon_type == payload.addon_type)
    )
    unit = ADDON_UNIT_PRICES_CENTS.get(payload.addon_type, 0)
    if existing:
        existing.quantity = payload.quantity
        existing.unit_price_cents = unit
        existing.status = "active"
        existing.notes = payload.notes
        existing.updated_at = datetime.now(timezone.utc)
        addon = existing
    else:
        addon = BillingAddOn(
            workspace_id=root.id,
            addon_type=payload.addon_type,
            quantity=payload.quantity,
            unit_price_cents=unit,
            status="active",
            notes=payload.notes,
            created_by_id=admin.id,
        )
        session.add(addon)
    session.add(
        AuditEvent(
            workspace_id=root.id,
            actor_id=admin.id,
            action="admin.addon_upserted",
            details={"addon_type": payload.addon_type, "quantity": payload.quantity},
        )
    )
    await session.commit()
    await session.refresh(addon)
    return map_addon(addon)


@router.delete("/admin/billing/addons/{addon_type}", response_model=MessageResponse)
async def admin_cancel_addon(
    addon_type: str,
    workspace_id: UUID,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    """Platform admin only: cancel a recurring boost."""
    cleaned = (addon_type or "").strip()
    if cleaned not in ADDON_UNIT_PRICES_CENTS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown add-on type")
    root = await billing_workspace(session, workspace_id)
    existing = await session.scalar(
        select(BillingAddOn).where(
            BillingAddOn.workspace_id == root.id,
            BillingAddOn.addon_type == cleaned,
            BillingAddOn.status == "active",
        )
    )
    if existing is None:
        return MessageResponse(message="Boost already inactive")
    existing.status = "canceled"
    existing.updated_at = datetime.now(timezone.utc)
    session.add(
        AuditEvent(
            workspace_id=root.id,
            actor_id=admin.id,
            action="admin.addon_canceled",
            details={"addon_type": cleaned},
        )
    )
    await session.commit()
    return MessageResponse(message="Boost cancelled")
