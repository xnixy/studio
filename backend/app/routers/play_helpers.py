"""Shared helpers for Play routes (generate + face library)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.media_signing import (
    ASSET_METADATA_MEDIA_KEYS,
    sign_media_fields,
    sign_media_url,
)
from app.models import User, VideoAsset, VideoProject, VideoScene
from app.schemas.play import PlayFaceDto, PlayGenerationDto

PLAY_PROJECT_TITLE = "Play"
PLAY_META_FLAG = "play_workspace"

PLATFORM_PRESETS: dict[str, tuple[str, str, int]] = {
    "tiktok": ("tiktok", "9:16", 15),
    "reels": ("instagram_reels", "9:16", 15),
    "shorts": ("youtube_shorts", "9:16", 15),
    "feed": ("meta_feed", "1:1", 15),
    "custom": ("tiktok", "9:16", 15),
}


def normalize_play_mode(mode: str) -> str:
    """Photo is gone. Old lipsync clients become Talking."""
    raw = (mode or "").strip().lower()
    if raw == "lipsync":
        return "avatar"
    return raw



def map_generation(asset: VideoAsset, settings: Settings) -> PlayGenerationDto:
    meta = dict(asset.asset_metadata or {})
    # Prefer durable storage over ephemeral provider CDNs (xAI/Kling tmp links expire).
    raw_url = asset.storage_url or asset.provider_url
    # Relative signed /api/media. The SPA and phone join their own API origin.
    # Do not bake PUBLIC_API_BASE_URL into the DTO (Tailscale http on an https
    # page is mixed content, so play and download both fail).
    if raw_url:
        url = sign_media_url(raw_url, settings) or raw_url
    else:
        url = None
    # Prefer a still from the finished clip. Face plate only while processing
    # (or as last resort if extract has not run yet).
    face_still = meta.get("face_image_url")
    raw_poster = meta.get("clip_poster_url") or meta.get("poster_url")
    if (
        asset.asset_type == "video"
        and asset.status == "ready"
        and raw_poster
        and face_still
        and str(raw_poster) == str(face_still)
        and not meta.get("clip_poster")
    ):
        raw_poster = None
    if not raw_poster:
        if asset.asset_type == "image":
            raw_poster = raw_url
        else:
            raw_poster = face_still
    poster_url = sign_media_url(str(raw_poster), settings) if raw_poster else None
    mode = str(meta.get("play_mode") or ("image" if asset.asset_type == "image" else "video"))
    if mode == "lipsync":
        mode = "avatar"
    platform = str(meta.get("play_platform") or "tiktok")
    # Sign media fields inside metadata so clients that read meta.poster_url /
    # clip_poster_url / face_image_url (img tags, mobile Image) get a usable sig.
    public_meta = {
        k: v
        for k, v in meta.items()
        if k not in {"provider_response", "provider_prompt"}
    }
    public_meta = sign_media_fields(public_meta, settings, keys=ASSET_METADATA_MEDIA_KEYS)
    return PlayGenerationDto(
        id=asset.id,
        workspace_id=asset.workspace_id,
        mode=mode,
        platform=platform,
        prompt=asset.prompt,
        status=asset.status,
        asset_type=asset.asset_type,
        provider=asset.provider or asset.source,
        provider_model=asset.provider_model,
        model_id=str(meta.get("model_id")) if meta.get("model_id") else None,
        url=url,
        poster_url=poster_url,
        error_message=asset.error_message,
        video_project_id=asset.video_project_id,
        created_at=asset.created_at,
        metadata=public_meta,
    )


def is_face_asset(asset: VideoAsset) -> bool:
    meta = dict(asset.asset_metadata or {})
    return meta.get("mode") == "avatar_source_image" or meta.get("face_library") is True


def is_play_ref_asset(asset: VideoAsset) -> bool:
    meta = dict(asset.asset_metadata or {})
    return meta.get("play_ref") is True


def is_hidden_from_clips(asset: VideoAsset) -> bool:
    """Face library stills and multi-ref materials must not appear in Clips."""
    return is_face_asset(asset) or is_play_ref_asset(asset)


def map_play_ref(asset: VideoAsset, settings: Settings) -> "PlayRefDto":
    from app.schemas.play import PlayRefDto

    meta = dict(asset.asset_metadata or {})
    raw_url = asset.storage_url or asset.provider_url
    url = sign_media_url(raw_url, settings) if raw_url else None
    kind_raw = str(meta.get("ref_kind") or asset.asset_type or "image")
    kind = kind_raw if kind_raw in ("image", "video", "audio") else "image"
    duration = meta.get("duration_seconds")
    duration_f = float(duration) if isinstance(duration, (int, float)) else None
    label = meta.get("label") or meta.get("original_filename")
    return PlayRefDto(
        id=asset.id,
        workspace_id=asset.workspace_id,
        kind=kind,  # type: ignore[arg-type]
        url=url,
        duration_seconds=duration_f,
        label=str(label)[:80] if label else None,
        status=asset.status,
        created_at=asset.created_at,
    )


def _face_display_label(asset: VideoAsset, meta: dict) -> str:
    """Display name for the face, not the consent/rights holder name."""
    raw_label = meta.get("label")
    consent = meta.get("consent_name")
    # Prefer explicit label only when it is not just a copy of consent name
    if raw_label and str(raw_label).strip():
        label = str(raw_label).strip()
        if not consent or label.casefold() != str(consent).strip().casefold():
            return label[:80]
    source_kind = str(meta.get("source_kind") or ("generated" if asset.source == "xai" else "upload"))
    if source_kind == "generated" and asset.prompt and asset.prompt.strip():
        # First phrase of the face description
        text = asset.prompt.strip().replace("\n", " ")
        return (text[:48] + "…") if len(text) > 48 else text
    filename = meta.get("original_filename")
    if filename and str(filename).strip():
        stem = str(filename).rsplit(".", 1)[0].strip()
        if stem:
            return stem[:80]
    if source_kind == "starter":
        return "Starter face"
    return "Uploaded face" if source_kind == "upload" else "Generated face"


def map_face(asset: VideoAsset, settings: Settings) -> PlayFaceDto:
    meta = dict(asset.asset_metadata or {})
    raw_url = asset.storage_url or asset.provider_url
    url = sign_media_url(raw_url, settings) if raw_url else None
    source_kind = str(meta.get("source_kind") or ("generated" if asset.source == "xai" else "upload"))
    starter_raw = meta.get("starter_id")
    starter_id = str(starter_raw).strip() if starter_raw else None
    parent_raw = meta.get("parent_face_id")
    parent_face_id = None
    if parent_raw:
        try:
            parent_face_id = UUID(str(parent_raw).strip())
        except (ValueError, TypeError, AttributeError):
            parent_face_id = None
    bound_raw = meta.get("bound_voice_id")
    bound_voice_id = str(bound_raw).strip() if bound_raw else None
    if not bound_voice_id:
        bound_voice_id = None
    prev_raw = meta.get("previous_url")
    previous_url = sign_media_url(str(prev_raw), settings) if prev_raw else None
    return PlayFaceDto(
        id=asset.id,
        workspace_id=asset.workspace_id,
        label=_face_display_label(asset, meta),
        url=url,
        source_kind=source_kind,
        consent_name=str(meta["consent_name"]) if meta.get("consent_name") else None,
        prompt=asset.prompt,
        status=asset.status,
        created_at=asset.created_at,
        starter_id=starter_id or None,
        parent_face_id=parent_face_id,
        bound_voice_id=bound_voice_id,
        previous_url=previous_url,
    )


async def get_or_create_play_project(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user: User,
    platform_key: str,
) -> VideoProject:
    platform, aspect, duration = PLATFORM_PRESETS.get(platform_key, PLATFORM_PRESETS["tiktok"])
    existing = await session.scalar(
        select(VideoProject)
        .options(selectinload(VideoProject.scenes), selectinload(VideoProject.assets))
        .where(
            VideoProject.workspace_id == workspace_id,
            VideoProject.title == PLAY_PROJECT_TITLE,
        )
        .order_by(VideoProject.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        meta = dict(existing.project_metadata or {})
        # Always re-apply platform/aspect from this request so chat filters stick.
        existing.platform = platform
        existing.aspect_ratio = aspect
        existing.target_duration_seconds = duration
        if not meta.get(PLAY_META_FLAG):
            meta[PLAY_META_FLAG] = True
            existing.project_metadata = meta
        return existing

    project = VideoProject(
        workspace_id=workspace_id,
        title=PLAY_PROJECT_TITLE,
        platform=platform,
        aspect_ratio=aspect,
        target_duration_seconds=duration,
        status="draft",
        created_by_id=user.id,
        project_metadata={PLAY_META_FLAG: True},
    )
    session.add(project)
    await session.flush()
    return project


async def next_scene(
    session: AsyncSession,
    project: VideoProject,
    prompt: str,
    *,
    spoken_text: str | None = None,
) -> VideoScene:
    await session.refresh(project, attribute_names=["scenes"])
    next_index = 0
    if project.scenes:
        next_index = max(s.sequence_index for s in project.scenes) + 1
    start_ms = next_index * 15_000
    scene = VideoScene(
        video_project_id=project.id,
        sequence_index=next_index,
        scene_type="storyboard",
        start_time_ms=start_ms,
        end_time_ms=start_ms + 15_000,
        visual_prompt=prompt.strip(),
        spoken_text=spoken_text.strip() if spoken_text and spoken_text.strip() else None,
        on_screen_text=None,
        transition="cut",
        scene_metadata={"play": True},
    )
    session.add(scene)
    await session.flush()
    return scene
