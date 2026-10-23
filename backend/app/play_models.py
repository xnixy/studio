"""Playground model catalog (multi-model picker) with token costs.

Clip is Seedance only: Fast is 2.0-fast (15s), Advanced is 2.5 (30s). Grok stills
and grok-4.6 assist stay. ``token_cost`` is how many units of the credit_meter to
reserve per generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlayModality = Literal["image", "video", "avatar", "lipsync"]

# One take: 15s Fast / 30s on 2.5. Longer talk is Extend (another card).
CLIP_FAST_MAX_SECONDS = 15
CLIP_ADVANCED_MAX_SECONDS = 30
TALKING_MAX_SECONDS = CLIP_ADVANCED_MAX_SECONDS


@dataclass(frozen=True)
class PlayModel:
    id: str
    label: str
    modality: PlayModality
    provider: str
    """Provider model string sent to the API."""
    provider_model: str
    blurb: str
    # Meter reserved against: image_generation | video_generation | avatar_lipsync
    credit_meter: str
    """How many meter tokens this generation burns."""
    token_cost: int = 1
    default: bool = False
    enabled: bool = True
    max_duration_seconds: int | None = None
    # Video: whether a face plate can ride along as identity (referenceImages /
    # seedance identity, etc.). False for engines that only accept text or a
    # true first-frame image (e.g. Veo 3.1 Lite). Talking models stay True.
    supports_face_reference: bool = True


# Token costs are relative product units (not provider API tokens).
# Image: 1–5 · Video/avatar: 5–12 · Lip-sync: 5
PLAY_MODELS: tuple[PlayModel, ...] = (
    PlayModel(
        id="xai-image-quality",
        label="Grok Image 2.0",
        modality="image",
        provider="xai",
        provider_model="grok-imagine-image-2.0",
        blurb="Latest Grok stills. Best for product and feed.",
        credit_meter="image_generation",
        token_cost=2,
    ),
    PlayModel(
        id="xai-image-fast",
        label="Grok Image Fast",
        modality="image",
        provider="xai",
        provider_model="grok-imagine-image",
        blurb="Quicker stills when you want volume.",
        credit_meter="image_generation",
        token_cost=1,
        default=True,
    ),
    PlayModel(
        id="nano-banana-2",
        label="Nano Banana 2",
        modality="image",
        provider="gemini",
        provider_model="gemini-3.1-flash-image",
        blurb="Google Gemini stills. Strong text and detail.",
        credit_meter="image_generation",
        token_cost=3,
    ),
    PlayModel(
        id="nano-banana-2-lite",
        label="Nano Banana 2 Lite",
        modality="image",
        provider="gemini",
        provider_model="gemini-3.1-flash-lite-image",
        blurb="Faster Gemini stills when you want volume.",
        credit_meter="image_generation",
        token_cost=2,
    ),
    PlayModel(
        id="nano-banana-pro",
        label="Nano Banana Pro",
        modality="image",
        provider="gemini",
        provider_model="gemini-3-pro-image",
        blurb="Top Gemini stills for hard prompts and brand work.",
        credit_meter="image_generation",
        token_cost=5,
    ),
    # Video
    PlayModel(
        id="seedance-2-5",
        label="Seedance 2.5",
        modality="video",
        provider="seedance",
        provider_model="seedance-2-5",
        blurb="Latest Seedance. Up to 30s, 720p, with audio. Text, image, or multi-ref.",
        credit_meter="video_generation",
        token_cost=12,
        max_duration_seconds=CLIP_ADVANCED_MAX_SECONDS,
    ),
    PlayModel(
        id="seedance-2-0-fast",
        label="Seedance 2.0 Fast",
        modality="video",
        provider="seedance",
        provider_model="seedance-2-0-fast",
        blurb="Faster Seedance when you want volume over max detail.",
        credit_meter="video_generation",
        token_cost=8,
        default=True,
        max_duration_seconds=CLIP_FAST_MAX_SECONDS,
    ),
    # Avatar talking-head. Retired clip engines stay in poll for in-flight jobs.
    PlayModel(
        id="seedance-avatar",
        label="Seedance Avatar",
        modality="avatar",
        provider="seedance",
        provider_model="seedance-2-5",
        blurb="Seedance 2.5 talking clip from your face and spoken audio. Up to 30s.",
        credit_meter="video_generation",
        token_cost=12,
        max_duration_seconds=CLIP_ADVANCED_MAX_SECONDS,
    ),
    PlayModel(
        id="seedance-avatar-fast",
        label="Seedance Avatar Fast",
        modality="avatar",
        provider="seedance",
        provider_model="seedance-2-0-fast",
        blurb="Faster Seedance talking clips for drafts.",
        credit_meter="video_generation",
        token_cost=8,
        default=True,
        max_duration_seconds=CLIP_FAST_MAX_SECONDS,
    ),
)


# Retired Photo catalog ids still arrive from old clients.
_PHOTO_MODEL_ALIAS = {
    "seedance-photo-fast": "seedance-avatar-fast",
    "seedance-photo": "seedance-avatar",
}


def models_for_modality(modality: PlayModality, *, enabled_only: bool = True) -> list[PlayModel]:
    if modality == "lipsync":
        modality = "avatar"
    rows = [m for m in PLAY_MODELS if m.modality == modality]
    if enabled_only:
        rows = [m for m in rows if m.enabled]
    return rows


def get_play_model(model_id: str | None, modality: PlayModality) -> PlayModel:
    if modality == "lipsync":
        modality = "avatar"
    available = models_for_modality(modality)
    if not available:
        raise KeyError(f"No models for modality {modality}")
    if model_id:
        key = _PHOTO_MODEL_ALIAS.get(model_id.strip(), model_id.strip())
        for m in available:
            if m.id == key or m.provider_model == key:
                return m
    for m in available:
        if m.default:
            return m
    return available[0]


def token_cost_for(model_id: str | None, modality: PlayModality) -> int:
    """Tokens to reserve for a generation (always >= 1)."""
    try:
        model = get_play_model(model_id, modality)
    except KeyError:
        return 1
    return max(1, int(model.token_cost or 1))


def catalog_public(*, plan_name: str | None = None) -> list[dict]:
    """Public model list. Optional plan_name marks locked Advanced engines."""
    from app.plan_entitlements import ADVANCED_MIN_PLAN, model_lane, plan_allows_model

    rows: list[dict] = []
    for m in PLAY_MODELS:
        if not m.enabled:
            continue
        lane = model_lane(m)
        allowed = plan_allows_model(plan_name, m) if plan_name is not None else True
        rows.append(
            {
                "id": m.id,
                "label": m.label,
                "modality": m.modality,
                "provider": m.provider,
                "blurb": m.blurb,
                "credit_meter": m.credit_meter,
                "token_cost": m.token_cost,
                "default": m.default,
                "enabled": m.enabled,
                "max_duration_seconds": m.max_duration_seconds,
                "supports_face_reference": m.supports_face_reference,
                "lane": lane,
                "requires_plan": None if lane == "fast" else ADVANCED_MIN_PLAN,
                "locked": (not allowed) if plan_name is not None else (lane == "advanced"),
            }
        )
    return rows
