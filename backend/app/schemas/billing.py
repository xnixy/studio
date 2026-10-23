from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import PlanName

class PlanDto(BaseModel):
    name: PlanName
    label: str
    script_generation_limit: int
    voiceover_seconds_limit: int
    workspace_limit: int
    seat_limit: int
    price_monthly: int
    video_credit_limit: int = 0
    image_generation_limit: int = 0
    avatar_lipsync_limit: int = 0
    play_video_limit: int = 0
    play_avatar_limit: int = 0
    play_clip_limit: int = 0
    play_still_limit: int = 0
    play_face_limit: int = 0
    play_lipsync_limit: int = 0
    storage_gb_limit: int = 0
    priority_rendering: bool = False


class PlanEntitlementsDto(BaseModel):
    """Create access for this plan (modes + Advanced model lane)."""

    modes: list[str] = Field(default_factory=list)
    advanced_models: bool = False
    min_plan_for_advanced: str = "starter"
    suggested_upgrade: str = "starter"


class BillingStatusDto(BaseModel):
    workspace_id: UUID
    billing_workspace_id: UUID
    plan: PlanName
    status: str
    stripe_configured: bool
    plans: list[PlanDto]
    # Product mode for frontend nav / feature walls
    plan_track: Literal["content", "static", "ads"] = "content"
    features: list[str] = Field(default_factory=list)
    suggested_upgrade: PlanName | None = None
    entitlements: PlanEntitlementsDto = Field(default_factory=PlanEntitlementsDto)
    script_generations_used: int
    script_generations_remaining: int
    voiceover_seconds_used: int
    voiceover_seconds_remaining: int
    image_generations_used: int = 0
    image_generations_remaining: int = 0
    video_generations_used: int = 0
    video_generations_remaining: int = 0
    avatar_lipsyncs_used: int = 0
    avatar_lipsyncs_remaining: int = 0
    # Per-function Play meters
    play_video_used: int = 0
    play_video_remaining: int = 0
    play_avatar_used: int = 0
    play_avatar_remaining: int = 0
    play_clip_used: int = 0
    play_clip_remaining: int = 0
    play_still_used: int = 0
    play_still_remaining: int = 0
    play_face_used: int = 0
    play_face_remaining: int = 0
    play_lipsync_used: int = 0
    play_lipsync_remaining: int = 0
    period_start: datetime
    period_end: datetime
    cancel_at_period_end: bool


class CheckoutRequest(BaseModel):
    workspace_id: UUID
    plan: PlanName


class BillingSessionDto(BaseModel):
    url: str | None
    configured: bool
    message: str


class UsageEventDto(BaseModel):
    id: UUID
    event_type: str
    quantity: int
    status: str
    created_at: datetime


AddOnType = Literal[
    "seats",
    "video_credits",
    "image_generations",
    "avatar_lipsyncs",
    "script_generations",
    "voiceover_minutes",
    "storage_gb",
    "priority_rendering",
]


CreditPackName = Literal[
    "video_10",
    "video_25",
    "image_50",
    "voice_30m",
]


class BillingAddOnUpsertRequest(BaseModel):
    """Admin grant only (user self-service free upsert is disabled)."""

    workspace_id: UUID
    addon_type: AddOnType
    quantity: int = Field(default=1, ge=1, le=500)
    notes: str | None = Field(default=None, max_length=500)


class BillingAddOnDto(BaseModel):
    id: UUID
    workspace_id: UUID
    addon_type: AddOnType
    quantity: int
    unit_price_cents: int
    status: Literal["active", "canceled"]
    notes: str | None
    monthly_total_cents: int
    created_at: datetime
    updated_at: datetime


class CreditPackDto(BaseModel):
    name: CreditPackName
    label: str
    description: str
    price_cents: int
    grants: dict[str, int] = Field(default_factory=dict)
    stripe_configured: bool = False


class CreditPackCheckoutRequest(BaseModel):
    workspace_id: UUID
    pack: CreditPackName


class BillingCreditGrantDto(BaseModel):
    id: UUID
    workspace_id: UUID
    pack_name: str
    label: str
    grants: dict[str, int] = Field(default_factory=dict)
    amount_cents: int
    status: Literal["active", "refunded", "expired"]
    period_start: datetime
    period_end: datetime
    created_at: datetime


class EffectiveLimitsDto(BaseModel):
    plan: PlanName
    seat_limit: int
    video_credit_limit: int
    image_generation_limit: int = 0
    avatar_lipsync_limit: int = 0
    storage_gb_limit: int
    priority_rendering: bool
    script_generation_limit: int
    voiceover_seconds_limit: int
    addons: list[BillingAddOnDto] = Field(default_factory=list)
    credit_grants: list[BillingCreditGrantDto] = Field(default_factory=list)
    packs: list[CreditPackDto] = Field(default_factory=list)

__all__ = [
    "PlanDto",
    "PlanEntitlementsDto",
    "BillingStatusDto",
    "CheckoutRequest",
    "BillingSessionDto",
    "UsageEventDto",
    "AddOnType",
    "CreditPackName",
    "BillingAddOnUpsertRequest",
    "BillingAddOnDto",
    "CreditPackDto",
    "CreditPackCheckoutRequest",
    "BillingCreditGrantDto",
    "EffectiveLimitsDto",
]
