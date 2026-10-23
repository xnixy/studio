"""Plan entitlements for Create models (Fast vs Advanced).

Free: all modes, Seedance Fast (and Grok Fast stills).
Starter+: Seedance 2.5 and other Advanced stills (Nano Banana, Grok Quality).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.plans import PAID_PLAN_NAMES, plan_for
from app.play_models import PlayModel, get_play_model

ModelLane = Literal["fast", "advanced"]

# Paid plan required to run Advanced (non-Fast) models.
ADVANCED_MIN_PLAN = "starter"

# Stable API error code for clients (paywall sheet).
CODE_ADVANCED_REQUIRED = "plan_advanced_required"

# Modes free users may use (all Create types).
FREE_MODES = frozenset({"image", "video", "avatar"})


@dataclass(frozen=True)
class PlanEntitlements:
    plan: str
    modes: tuple[str, ...]
    advanced_models: bool
    min_plan_for_advanced: str
    suggested_upgrade: str


def plan_entitlements(plan_name: str | None) -> PlanEntitlements:
    plan = plan_for(plan_name)
    paid = plan.name in PAID_PLAN_NAMES
    upgrade = "starter" if plan.name == "free" else (
        "creator" if plan.name == "starter" else ("studio" if plan.name == "creator" else "studio")
    )
    return PlanEntitlements(
        plan=plan.name,
        modes=tuple(sorted(FREE_MODES)),
        advanced_models=paid,
        min_plan_for_advanced=ADVANCED_MIN_PLAN,
        suggested_upgrade=upgrade if not paid else plan.name,
    )


def model_lane(model: PlayModel) -> ModelLane:
    """Fast = Seedance *-fast / mini, plus Grok stills. 2.5 and Nano Banana are Advanced."""
    mid = (model.id or "").strip().lower()
    provider = (model.provider or "").strip().lower()
    if model.modality == "image":
        return "fast" if provider == "xai" else "advanced"
    if "fast" in mid or mid.endswith("-mini") or "mini" in mid:
        return "fast"
    return "advanced"


def plan_allows_model(plan_name: str | None, model: PlayModel) -> bool:
    if model_lane(model) == "fast":
        return True
    return plan_entitlements(plan_name).advanced_models


def plan_allows_model_id(plan_name: str | None, model_id: str | None, modality: str) -> bool:
    try:
        model = get_play_model(model_id, modality)  # type: ignore[arg-type]
    except KeyError:
        return True
    return plan_allows_model(plan_name, model)


def raise_if_model_not_allowed(plan_name: str | None, model: PlayModel) -> None:
    if plan_allows_model(plan_name, model):
        return
    ent = plan_entitlements(plan_name)
    upgrade_label = plan_for(ent.min_plan_for_advanced).label
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": (
                f"Advanced models need a paid plan. "
                f"Upgrade to {upgrade_label} to unlock {model.label}."
            ),
            "code": CODE_ADVANCED_REQUIRED,
            "suggested_plan": ent.min_plan_for_advanced,
            "model_id": model.id,
            "lane": "advanced",
        },
    )


async def require_play_model_for_workspace(
    session: AsyncSession,
    workspace_id: UUID,
    model: PlayModel,
) -> None:
    """Load workspace plan and reject Advanced models on free."""
    from app.workspace_access import effective_plan_name, get_subscription

    sub = await get_subscription(session, workspace_id)
    raise_if_model_not_allowed(effective_plan_name(sub), model)


def entitlements_public(plan_name: str | None) -> dict:
    ent = plan_entitlements(plan_name)
    return {
        "modes": list(ent.modes),
        "advanced_models": ent.advanced_models,
        "min_plan_for_advanced": ent.min_plan_for_advanced,
        "suggested_upgrade": ent.suggested_upgrade,
    }
