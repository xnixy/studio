"""Playground generate DTOs (chat-first media)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


PlayMode = Literal["image", "video", "avatar", "lipsync"]
PlayPlatform = Literal["tiktok", "reels", "shorts", "feed", "custom"]
PlayRefKind = Literal["image", "video", "audio"]


class PlayModelDto(BaseModel):
    id: str
    label: str
    modality: str
    provider: str
    blurb: str
    credit_meter: str
    """Meter tokens burned per generation (premium models cost more)."""
    token_cost: int = 1
    default: bool = False
    enabled: bool = True
    max_duration_seconds: int | None = None
    """Whether Video mode may attach a face plate as identity reference."""
    supports_face_reference: bool = True
    """fast = Seedance Fast (and Grok stills); advanced = Seedance 2.5 / Nano Banana."""
    lane: Literal["fast", "advanced"] = "fast"
    """Minimum plan name required when lane is advanced (e.g. starter)."""
    requires_plan: str | None = None
    """True when the caller's plan cannot use this model (or when unauthenticated: advanced)."""
    locked: bool = False


class PlayGenerateRequest(BaseModel):
    workspace_id: UUID
    mode: PlayMode = "video"
    platform: PlayPlatform = "tiktok"
    prompt: str = Field(min_length=1, max_length=4000)
    model: str | None = Field(default=None, max_length=80)
    """Required for Talking. Optional for Scene."""
    face_asset_id: UUID | None = None
    """Legacy Photo place. Joined into the Talking prompt. Never spoken on its own."""
    scene: str = Field(default="", max_length=2000)
    voice: str | None = Field(default="jessica", max_length=64)
    """Clip length for video/avatar (seconds). Clamped by model max. Ignored for image."""
    duration_seconds: int | None = Field(default=None, ge=1, le=30)
    """Output resolution for video models that support it (Seedance: 480p–4k)."""
    resolution: str | None = Field(default=None, max_length=16)
    """Whether the model should generate audio when supported (Seedance default true)."""
    generate_audio: bool | None = None
    """Return last frame URL when the provider supports it (Seedance)."""
    return_last_frame: bool | None = None
    """Ordered play ref asset ids (image/video/audio). Max 12. Face is separate."""
    reference_asset_ids: list[UUID] = Field(default_factory=list, max_length=12)
    """Optional per-reference roles, positionally matched to reference_asset_ids.

    Names what each image is for so the model can act on it ("her friend",
    "the product", "the location"). Omitted or blank entries fall back to a
    generic label. Extra entries are ignored.
    """
    reference_roles: list[str] = Field(default_factory=list, max_length=12)
    """Batch size for Seedance video/avatar. Other providers clamp to 1."""
    count: int = Field(default=1, ge=1, le=10)
    """Continue from a ready video clip (Seedance reference-to-video)."""
    continue_from_asset_id: UUID | None = None
    """Source clip for revoice (lip-sync with exact script + voice from a prior clip's face)."""
    revoice_of_asset_id: UUID | None = None
    """Client idempotency key (same as Idempotency-Key header). Max 128 chars."""
    client_request_id: str | None = Field(default=None, max_length=128)


class PlayQuoteRequest(BaseModel):
    """Estimate tokens for the current Create controls (same math as reserve)."""

    mode: PlayMode = "video"
    model: str | None = Field(default=None, max_length=80)
    """Omit or null for Auto length (Talking sizes from spoken line when prompt is set)."""
    duration_seconds: int | None = Field(default=None, ge=1, le=30)
    """Used with Auto duration for Talking (spoken line estimate)."""
    prompt: str | None = Field(default=None, max_length=4000)
    resolution: str | None = Field(default=None, max_length=16)
    count: int = Field(default=1, ge=1, le=10)
    generate_audio: bool | None = True
    return_last_frame: bool | None = False
    """A face plate counts as a reference image, and Video mode may carry one."""
    has_face: bool = False
    ref_image_count: int = Field(default=0, ge=0, le=12)
    ref_video_count: int = Field(default=0, ge=0, le=3)
    ref_audio_count: int = Field(default=0, ge=0, le=3)
    continue_from: bool = False
    """Talking + cloned voice also reserves voiceover seconds. No extra lip-sync credits."""
    cloned_voice: bool = False
    """Ignored. Photo no longer spends a still credit on a plate."""
    has_scene: bool = False


class PlayQuoteResponse(BaseModel):
    meter: str
    per_item: int
    count: int
    total: int
    base: int
    breakdown: dict = Field(default_factory=dict)


class PlayAssistMessage(BaseModel):
    """One turn of the Create conversation. Only the two roles the UI renders."""

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class PlayAssistDraft(BaseModel):
    """The generation as it currently stands, in the terms the composer owns.

    Everything is optional: the first turn usually carries a scene and nothing
    else, and the planner fills the rest in as the conversation settles it.
    """

    scene: str = Field(default="", max_length=2000)
    line: str = Field(default="", max_length=2000)
    duration_seconds: int | None = None
    voice: str | None = None
    """Which paid job this draft will run. Server-settled. Never trusted from the chat reply."""
    kind: Literal["avatar", "lipsync", "video"] | None = None
    """Seedance Fast or 2.5 catalog id. Settled from speech length and chat, not Options."""
    model: str | None = Field(default=None, max_length=80)
    """Output resolution. Default 720p. 1080p/4k only on Fast."""
    resolution: str | None = Field(default=None, max_length=16)
    """Speech over 30s: first 30s generates, then Extend for the rest."""
    extend_rest: bool = False
    """Square when they asked. Otherwise leave empty (client keeps 9:16)."""
    platform: str | None = Field(default=None, max_length=16)


class PlayAssistSource(BaseModel):
    """A clip this request follows on from.

    Without it the planner is proposing a next shot, a new script, or a fix for a
    failure it cannot see, which is worse than not asking at all.
    """

    kind: Literal["continue", "revoice", "retry"]
    """The prior clip's prompt, so the planner knows what came before."""
    prompt: str = Field(default="", max_length=4000)
    """Why the prior attempt failed. Only meaningful for a retry."""
    error: str = Field(default="", max_length=600)


class PlayAssistRequest(BaseModel):
    workspace_id: UUID
    mode: PlayMode = "avatar"
    draft: PlayAssistDraft = Field(default_factory=PlayAssistDraft)
    messages: list[PlayAssistMessage] = Field(default_factory=list, max_length=12)
    source: PlayAssistSource | None = None


class PlayAssistChoice(BaseModel):
    """One tappable alternative for a decision the planner already made.

    Never a gate. The planner picks, the app shows the pick selected with the
    alternatives beside it, and tapping is optional, so nobody in a hurry has to
    answer a question before anything happens.
    """

    label: str = Field(max_length=48)
    """What tapping it means, sent back as the user's next turn."""
    value: str = Field(max_length=200)
    selected: bool = False


class PlayAssistOptions(BaseModel):
    """A single decision worth surfacing, with the choice already applied."""

    header: str = Field(max_length=32)
    choices: list[PlayAssistChoice] = Field(default_factory=list, max_length=4)


class PlayAssistResponse(BaseModel):
    """What to show in the thread, and what to put back in the fields."""

    reply: str
    draft: PlayAssistDraft
    """At most one decision per turn, so the card never becomes a form."""
    options: PlayAssistOptions | None = None
    # False while something material is still unsettled, so the composer can keep
    # the conversation open instead of generating on a guess.
    ready: bool = False
    # Server-side facts about the pending clip, never model output. The composer
    # shows these so nobody pays for a length or a read they did not expect.
    summary: list[str] = Field(default_factory=list)


class PlayGenerationDto(BaseModel):
    id: UUID
    workspace_id: UUID
    mode: str
    platform: str
    prompt: str | None
    status: str
    asset_type: str
    provider: str | None = None
    provider_model: str | None = None
    model_id: str | None = None
    url: str | None = None
    """Still frame for list thumbnails (face plate or explicit poster)."""
    poster_url: str | None = None
    error_message: str | None = None
    video_project_id: UUID | None = None
    created_at: datetime
    metadata: dict = Field(default_factory=dict)


class PlayGenerateResponse(BaseModel):
    generation: PlayGenerationDto
    """All items when count > 1; always includes generation as first when non-empty."""
    generations: list[PlayGenerationDto] = Field(default_factory=list)
    message: str | None = None


class PlayFaceDto(BaseModel):
    """Reusable workspace face for avatar / lip-sync."""

    id: UUID
    workspace_id: UUID
    label: str | None = None
    url: str | None = None
    source_kind: str = "upload"  # upload | generated | starter
    consent_name: str | None = None
    prompt: str | None = None
    status: str = "ready"
    created_at: datetime
    """When set, this face was copied from a Studio starter (maya, jordan, …)."""
    starter_id: str | None = None
    parent_face_id: UUID | None = None
    bound_voice_id: str | None = None
    previous_url: str | None = None


class PlayFaceGenerateRequest(BaseModel):
    workspace_id: UUID
    prompt: str = Field(min_length=3, max_length=1200)
    """Optional display name. Defaults to a short form of the face description."""
    label: str | None = Field(default=None, max_length=120)
    """Rights-holder name (consent). Not used as the face display name."""
    consent_name: str = Field(min_length=2, max_length=120)
    consent_confirmed: bool = False
    """Play image model id (e.g. xai-image-quality, nano-banana-2)."""
    model: str | None = Field(default=None, max_length=80)


class PlayFaceEditRequest(BaseModel):
    workspace_id: UUID
    instruction: str = Field(min_length=1, max_length=400)
    kind: Literal["touchup", "look"] = "touchup"
    save: Literal["replace", "new"] = "replace"
    model: str | None = Field(default=None, max_length=80)


class PlayFaceBindVoiceRequest(BaseModel):
    workspace_id: UUID
    bound_voice_id: str | None = Field(default=None, max_length=80)


class PlayRefDto(BaseModel):
    """Uploaded material for Seedance multi-ref generation."""

    id: UUID
    workspace_id: UUID
    kind: PlayRefKind
    url: str | None = None
    duration_seconds: float | None = None
    label: str | None = None
    status: str = "ready"
    created_at: datetime
