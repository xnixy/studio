from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class PlanLimits:
    name: str
    label: str
    script_generation_limit: int
    voiceover_seconds_limit: int
    workspace_limit: int
    seat_limit: int
    price_monthly: int
    # Legacy media pools (kept for packs/addons + older events).
    video_credit_limit: int = 50
    image_generation_limit: int = 30
    avatar_lipsync_limit: int = 25
    # Per-function Play meters (preferred for new charges).
    play_video_limit: int = 50
    play_avatar_limit: int = 50
    play_still_limit: int = 30
    play_face_limit: int = 15
    play_lipsync_limit: int = 25
    storage_gb_limit: int = 2
    priority_rendering: bool = False


# Pricing posture:
# - Free + three paid tiers (Starter / Creator / Studio). No separate image track.
# - Subscription = access + seats + a monthly media sample.
# - Heavy volume is sold via credit packs (and optional recurring add-ons).
PLAN_CATALOG = (
    PlanLimits(
        "free",
        "Free",
        3,
        60,
        1,  # workspace_limit (always one personal account)
        1,  # seat_limit (owner only)
        0,
        video_credit_limit=10,
        image_generation_limit=12,  # aligned with play_still_limit
        avatar_lipsync_limit=5,
        play_video_limit=10,
        play_avatar_limit=10,
        play_still_limit=12,
        play_face_limit=5,
        play_lipsync_limit=5,
        storage_gb_limit=1,
    ),
    PlanLimits(
        "starter",
        "Starter",
        40,
        900,
        1,
        1,
        3_900,
        video_credit_limit=30,
        image_generation_limit=90,
        avatar_lipsync_limit=20,
        play_video_limit=30,
        play_avatar_limit=30,
        play_still_limit=70,
        play_face_limit=20,
        play_lipsync_limit=20,
        storage_gb_limit=8,
    ),
    PlanLimits(
        "creator",
        "Creator",
        100,
        2_400,
        1,
        1,
        9_900,
        video_credit_limit=75,
        image_generation_limit=200,
        avatar_lipsync_limit=50,
        play_video_limit=75,
        play_avatar_limit=75,
        play_still_limit=160,
        play_face_limit=40,
        play_lipsync_limit=50,
        storage_gb_limit=30,
    ),
    PlanLimits(
        "studio",
        "Studio",
        250,
        7_200,
        1,
        1,
        17_900,
        video_credit_limit=200,
        image_generation_limit=500,
        avatar_lipsync_limit=125,
        play_video_limit=200,
        play_avatar_limit=200,
        play_still_limit=400,
        play_face_limit=100,
        play_lipsync_limit=125,
        storage_gb_limit=100,
        priority_rendering=True,
    ),
)

PAID_PLAN_NAMES = ("starter", "creator", "studio")

# Recurring monthly boosts. Media add-on units convert to tokens in apply_addons.
ADDON_UNIT_PRICES_CENTS = {
    "seats": 2_000,
    "video_credits": 900,  # +5 video tokens
    "image_generations": 150,  # +3 image tokens
    "avatar_lipsyncs": 900,  # +5 clip tokens (legacy Photo addon)
    "script_generations": 100,
    "voiceover_minutes": 100,
    "storage_gb": 150,
    "priority_rendering": 4_900,
}

# How many meter tokens one recurring add-on unit grants
ADDON_TOKEN_GRANTS = {
    "video_credits": 5,
    "image_generations": 3,
    "avatar_lipsyncs": 5,
}

GRANTABLE_LIMIT_FIELDS = frozenset(
    {
        "script_generation_limit",
        "voiceover_seconds_limit",
        "video_credit_limit",
        "image_generation_limit",
        "avatar_lipsync_limit",
        "play_video_limit",
        "play_avatar_limit",
        "play_still_limit",
        "play_face_limit",
        "play_lipsync_limit",
        "storage_gb_limit",
    }
)


@dataclass(frozen=True)
class CreditPack:
    """One-time Stripe pack that grants extra monthly token budget for the purchase month."""

    name: str
    label: str
    description: str
    price_cents: int
    grants: dict[str, int]  # PlanLimits *_limit field → tokens to add


# Live sale catalog. Checkout and IAP product lists use this only.
CREDIT_PACK_CATALOG: tuple[CreditPack, ...] = (
    CreditPack(
        "video_10",
        "Clip credit pack",
        "50 clip credits this month.",
        9_000,
        {
            "video_credit_limit": 50,
            "play_video_limit": 50,
        },
    ),
    CreditPack(
        "video_25",
        "Clip credit pack (large)",
        "125 clip credits this month.",
        20_000,
        {
            "video_credit_limit": 125,
            "play_video_limit": 125,
        },
    ),
    CreditPack(
        "image_50",
        "Still credit pack",
        "150 still credits this month.",
        5_000,
        {
            "image_generation_limit": 150,
            "play_still_limit": 150,
            "play_face_limit": 50,  # 150 // 3, same ratio as apply_addons
        },
    ),
    CreditPack(
        "voice_30m",
        "Voice pack (30 min)",
        "30 extra minutes of clone TTS this month.",
        2_000,
        {"voiceover_seconds_limit": 1_800},
    ),
)

# Not for sale. Keep so Stripe/IAP that already charged still grant.
RETIRED_CREDIT_PACKS: tuple[CreditPack, ...] = (
    CreditPack(
        "lipsync_10",
        "Clip credit pack",
        "50 clip credits this month.",
        9_000,
        {
            "avatar_lipsync_limit": 50,
            "play_lipsync_limit": 50,
        },
    ),
    CreditPack(
        "scripts_25",
        "Script pack (25)",
        "25 extra script / concept generations this month.",
        2_000,
        {"script_generation_limit": 25},
    ),
    CreditPack(
        "creator_burst",
        "Creator burst",
        "40 clip credits, 45 still credits, and 15 min voice.",
        7_900,
        {
            "video_credit_limit": 25,
            "play_video_limit": 25,
            "image_generation_limit": 45,
            "play_still_limit": 45,
            "play_face_limit": 15,
            "avatar_lipsync_limit": 15,
            "play_lipsync_limit": 15,
            "voiceover_seconds_limit": 900,
        },
    ),
)


def clip_credit_limit(limits: PlanLimits) -> int:
    """Talking and Scene are one Clip pool. Leftover Photo caps fold in."""
    return (
        int(limits.play_avatar_limit or 0)
        + int(limits.play_video_limit or 0)
        + int(limits.play_lipsync_limit or 0)
    )


def sale_credit_pack_for(name: str | None) -> CreditPack | None:
    return next((pack for pack in CREDIT_PACK_CATALOG if pack.name == name), None)


def credit_pack_for(name: str | None) -> CreditPack | None:
    """Live pack, or a retired SKU still honored for fulfillment."""
    live = sale_credit_pack_for(name)
    if live is not None:
        return live
    return next((pack for pack in RETIRED_CREDIT_PACKS if pack.name == name), None)


def plan_for(name: str | None) -> PlanLimits:
    return next((plan for plan in PLAN_CATALOG if plan.name == name), PLAN_CATALOG[0])


LIMIT_OVERRIDE_FIELDS = {
    field
    for field in PlanLimits.__dataclass_fields__
    if field.endswith("_limit")
}


def apply_limit_overrides(base: PlanLimits, overrides: dict[str, int] | None) -> PlanLimits:
    """Apply absolute admin cap overrides.

    Ops UI edits legacy media keys (video_credit_limit, …). Create meters use
    play_* limits, so mirror those absolute overrides onto play meters when the
    corresponding play_* key is not set explicitly. Without this, extra usage
    from Accounts does not show on Billing → Usage this period.
    """
    clean = {
        key: max(0, int(value))
        for key, value in (overrides or {}).items()
        if key in LIMIT_OVERRIDE_FIELDS
    }
    if not clean:
        return base

    if "video_credit_limit" in clean:
        video_n = clean["video_credit_limit"]
        # Clip pool is play_video + play_avatar. Mirror the legacy key onto
        # play_video only so an override of 100 is +100 combined, not +200.
        clean.setdefault("play_video_limit", video_n)
    if "image_generation_limit" in clean:
        image_n = clean["image_generation_limit"]
        clean.setdefault("play_still_limit", image_n)
        clean.setdefault("play_face_limit", max(0, image_n // 3))
    if "avatar_lipsync_limit" in clean:
        clean.setdefault("play_lipsync_limit", clean["avatar_lipsync_limit"])

    return replace(base, **clean)


def apply_limit_grants(base: PlanLimits, grants: dict[str, int] | None) -> PlanLimits:
    """Add one-time pack grants (and similar) onto limit fields.

    Dual-writes legacy media keys onto Play meters when the grant only has the
    legacy key (old DB rows). Catalog packs already include both keys; expansion
    skips any play_* key already present so dual-written packs do not double-count.
    """
    if not grants:
        return base
    updates: dict[str, int] = {}
    for key, amount in grants.items():
        if key not in GRANTABLE_LIMIT_FIELDS and key not in LIMIT_OVERRIDE_FIELDS:
            continue
        if not key.endswith("_limit"):
            continue
        current = int(getattr(base, key, 0) or 0)
        updates[key] = current + max(0, int(amount))

    # Legacy → Play expansion for grants stored before dual-write catalog.
    if "video_credit_limit" in grants:
        video_n = max(0, int(grants["video_credit_limit"] or 0))
        if video_n:
            if "play_video_limit" not in grants:
                updates["play_video_limit"] = int(base.play_video_limit or 0) + video_n
    if "image_generation_limit" in grants:
        image_n = max(0, int(grants["image_generation_limit"] or 0))
        if image_n:
            if "play_still_limit" not in grants:
                updates["play_still_limit"] = int(base.play_still_limit or 0) + image_n
            if "play_face_limit" not in grants:
                updates["play_face_limit"] = int(base.play_face_limit or 0) + max(0, image_n // 3)
    if "avatar_lipsync_limit" in grants:
        lipsync_n = max(0, int(grants["avatar_lipsync_limit"] or 0))
        if lipsync_n and "play_lipsync_limit" not in grants:
            updates["play_lipsync_limit"] = int(base.play_lipsync_limit or 0) + lipsync_n

    return replace(base, **updates) if updates else base


def apply_addons(base: PlanLimits, addons: dict[str, int]) -> PlanLimits:
    """Merge active billing add-on quantities into plan limits (media = tokens)."""
    seats = base.seat_limit + int(addons.get("seats") or 0)
    video_boost = int(addons.get("video_credits") or 0) * ADDON_TOKEN_GRANTS["video_credits"]
    image_boost = int(addons.get("image_generations") or 0) * ADDON_TOKEN_GRANTS["image_generations"]
    lipsync_boost = int(addons.get("avatar_lipsyncs") or 0) * ADDON_TOKEN_GRANTS["avatar_lipsyncs"]
    video_credits = base.video_credit_limit + video_boost
    images = base.image_generation_limit + image_boost
    lipsyncs = base.avatar_lipsync_limit + lipsync_boost
    scripts = base.script_generation_limit + int(addons.get("script_generations") or 0)
    voice_seconds = base.voiceover_seconds_limit + int(addons.get("voiceover_seconds") or 0)
    voice_seconds += int(addons.get("voiceover_minutes") or 0) * 60
    storage = base.storage_gb_limit + int(addons.get("storage_gb") or 0)
    priority = base.priority_rendering or int(addons.get("priority_rendering") or 0) > 0
    return replace(
        base,
        seat_limit=seats,
        video_credit_limit=video_credits,
        image_generation_limit=images,
        avatar_lipsync_limit=lipsyncs,
        # Video add-ons top up the Clip pool once (play_video side).
        play_video_limit=base.play_video_limit + video_boost,
        play_avatar_limit=base.play_avatar_limit,
        play_still_limit=base.play_still_limit + image_boost,
        play_face_limit=base.play_face_limit + max(0, image_boost // 3),
        play_lipsync_limit=base.play_lipsync_limit + lipsync_boost,
        script_generation_limit=scripts,
        voiceover_seconds_limit=voice_seconds,
        storage_gb_limit=storage,
        priority_rendering=priority,
    )
