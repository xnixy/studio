"""Plan product modes: which product areas each plan may use.

Quotas still enforce volume. These flags decide whether a surface is part of the plan.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.plans import plan_for


FEATURE_STUDIO = "studio"
FEATURE_BILLING = "billing"
FEATURE_STATIC_ADS = "static_ads"

PLAY_FEATURES = frozenset(
    {
        FEATURE_STUDIO,
        FEATURE_BILLING,
        FEATURE_STATIC_ADS,
    }
)

PLAN_FEATURES: dict[str, frozenset[str]] = {
    "free": PLAY_FEATURES,
    "starter": PLAY_FEATURES,
    "creator": PLAY_FEATURES,
    "studio": PLAY_FEATURES,
}

UPGRADE_PATH = {
    "free": "starter",
    "starter": "creator",
    "creator": "studio",
    "studio": "studio",
}


@dataclass(frozen=True)
class PlanProductMode:
    plan: str
    track: str  # always "content" (single product track)
    features: frozenset[str]
    suggested_upgrade: str


def plan_product_mode(plan_name: str | None) -> PlanProductMode:
    plan = plan_for(plan_name)
    features = PLAN_FEATURES.get(plan.name, PLAY_FEATURES)
    upgrade = UPGRADE_PATH.get(plan.name, "starter")
    return PlanProductMode(plan=plan.name, track="content", features=features, suggested_upgrade=upgrade)


def plan_has_feature(plan_name: str | None, feature: str) -> bool:
    return feature in plan_product_mode(plan_name).features


def require_plan_feature(plan_name: str | None, feature: str) -> PlanProductMode:
    mode = plan_product_mode(plan_name)
    if feature not in mode.features:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Plan '{mode.plan}' does not include {feature}. Suggested upgrade: {mode.suggested_upgrade}",
        )
    return mode


def raise_if_feature_missing(plan_name: str | None, feature: str) -> None:
    mode = plan_product_mode(plan_name)
    if feature in mode.features:
        return
    label = plan_for(plan_name).label
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"{feature.replace('_', ' ').title()} is not included on the {label} plan. "
            f"Upgrade to {plan_for(mode.suggested_upgrade).label} (or higher) to unlock this feature."
        ),
    )
