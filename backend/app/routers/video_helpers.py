"""Shared video helpers used by Play + asset poll."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import Settings
from app.media_store import MediaStoreError, download_media_url, ensure_local_media, r2_enabled, store_file
from app.models import GenerationCost, User, VideoAsset, VideoProject, VideoRender
from app.schemas import VideoProviderStatusDto
from app.video_renderer import (
    VideoRenderError,
    extract_video_poster_frame,
    mp4_has_faststart,
    remux_mp4_faststart,
    strip_audio_from_video,
)
from app.workspace_access import require_permission
from app.routers.video_maps import *  # noqa: F403

SYNC_READY_STATUSES = {"COMPLETED", "COMPLETE", "SUCCEEDED", "SUCCESS", "DONE"}
SYNC_FAILED_STATUSES = {"FAILED", "ERROR", "CANCELED", "CANCELLED", "REJECTED"}


async def get_video_project(
    project_id: UUID, user: User, session: AsyncSession, permission: str = "projects.read"
) -> VideoProject:
    project = await session.scalar(
        select(VideoProject)
        .options(
            selectinload(VideoProject.scenes),
            selectinload(VideoProject.renders).selectinload(VideoRender.jobs),
            selectinload(VideoProject.renders).selectinload(VideoRender.caption_tracks),
            selectinload(VideoProject.assets),
        )
        .where(VideoProject.id == project_id)
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video project not found")
    await require_permission(session, project.workspace_id, user, permission)
    return project


def should_strip_scene_clip_audio(asset: VideoAsset) -> bool:
    if asset.asset_type != "video":
        return False
    if asset.source == "sync_labs" or asset.provider == "sync_labs":
        return False
    meta = asset.asset_metadata if isinstance(asset.asset_metadata, dict) else {}
    if meta.get("play") is True:
        return False
    mode = str(meta.get("mode") or "")
    play_mode = str(meta.get("play_mode") or "")
    if mode in {"avatar_lipsync", "lipsync"}:
        return False
    if play_mode in {"avatar", "video", "lipsync"}:
        return False
    return True


async def persist_provider_media(asset: VideoAsset, settings: Settings) -> str:
    if not asset.provider_url:
        raise MediaStoreError("Asset does not have a provider URL to persist")
    fallback = ".mp4" if asset.asset_type == "video" else ".jpg" if asset.asset_type == "image" else ".bin"
    path, storage_url = await download_media_url(
        url=asset.provider_url,
        settings=settings,
        subdir="video-assets",
        stem=asset.id,
        fallback_extension=fallback,
        max_bytes=512 * 1024 * 1024 if asset.provider == "sync_labs" else 250 * 1024 * 1024,
    )
    if should_strip_scene_clip_audio(asset):
        silent_path = path.with_name(f"{path.stem}-silent{path.suffix}")
        try:
            strip_audio_from_video(path, silent_path)
            storage_url = store_file(
                path=silent_path,
                subdir="video-assets",
                filename=silent_path.name,
                settings=settings,
                content_type="video/mp4",
            )
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "audio_stripped": True,
                "audio_policy": "scene_clips_silent_until_export_vo",
            }
            path = silent_path
        except VideoRenderError as exc:
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "audio_strip_error": str(exc)[:300],
            }
    # Progressive-friendly MP4 for iOS AVPlayer (moov at start). Best-effort.
    if asset.asset_type == "video" and path.suffix.lower() in {".mp4", ".m4v", ".mov"}:
        try:
            fast = remux_mp4_faststart(path)
            storage_url = store_file(
                path=fast,
                subdir="video-assets",
                filename=path.name if path.suffix.lower() == ".mp4" else f"{path.stem}.mp4",
                settings=settings,
                content_type="video/mp4",
            )
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "faststart": True,
            }
        except VideoRenderError as exc:
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "faststart_error": str(exc)[:300],
            }
    return storage_url


def provider_aspect_ratio(aspect_ratio: str) -> str:
    if aspect_ratio == "4:5":
        return "3:4"
    return aspect_ratio


async def get_asset(
    asset_id: UUID,
    user: User,
    session: AsyncSession,
    permission: str = "projects.read",
    *,
    missing: str | None = None,
) -> VideoAsset:
    asset = await session.get(VideoAsset, asset_id)
    if asset is None:
        if missing:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=missing)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video asset not found")
    await require_permission(session, asset.workspace_id, user, permission)
    return asset


def add_generation_cost(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    user_id: UUID | None,
    feature: str,
    provider: str = "xai",
    provider_model: str | None = None,
    provider_request_id: str | None = None,
    cost_usd_ticks: int | None = None,
    metadata: dict[str, object],
) -> None:
    if cost_usd_ticks is None:
        return
    session.add(
        GenerationCost(
            workspace_id=workspace_id,
            user_id=user_id,
            feature=feature,
            provider=provider,
            provider_model=provider_model,
            provider_request_id=provider_request_id,
            cost_usd_ticks=cost_usd_ticks,
            cost_metadata=metadata,
        )
    )


def sync_asset_status(provider_status: str) -> str:
    status_value = provider_status.upper()
    if status_value in SYNC_READY_STATUSES:
        return "ready"
    if status_value in SYNC_FAILED_STATUSES:
        return "failed"
    return "processing"


def maybe_attach_clip_poster(asset: VideoAsset, settings: Settings) -> None:
    """Replace face-plate poster_url with a still from the ready clip.

    Talking/avatar starts store the selected face as poster_url for the processing
    state. Once the video is ready, list thumbs must show the generated scene
    (new outfit/background), not the identity plate.
    """
    if asset.asset_type != "video" or asset.status != "ready":
        return
    meta = dict(asset.asset_metadata or {})
    if meta.get("clip_poster") is True:
        return

    # Seedance (and similar) may already attach a real last-frame still.
    last_frame = meta.get("last_frame_url")
    face = meta.get("face_image_url")
    poster = meta.get("poster_url")
    if isinstance(last_frame, str) and last_frame.strip():
        if not poster or poster == face:
            meta["poster_url"] = last_frame.strip()
        meta["clip_poster"] = True
        meta["clip_poster_url"] = str(meta.get("poster_url") or last_frame).strip()
        asset.asset_metadata = meta
        return

    source = asset.storage_url or asset.provider_url
    if not source:
        return
    try:
        video_path = ensure_local_media(str(source), settings)
        out_path = video_path.with_name(f"{video_path.stem}-poster.jpg")
        extract_video_poster_frame(video_path, out_path, at_seconds=0.4)
        stored = store_file(
            path=out_path,
            subdir="play",
            filename=f"{asset.id}-poster.jpg",
            settings=settings,
            content_type="image/jpeg",
        )
        # Keep face_image_url for identity UI; poster_url is the clip still.
        if face is None and poster and poster != stored:
            # Preserve prior face plate if it was only stored under poster_url.
            meta["face_image_url"] = poster
        meta["poster_url"] = stored
        meta["clip_poster_url"] = stored
        meta["clip_poster"] = True
        meta.pop("clip_poster_error", None)
        asset.asset_metadata = meta
    except Exception as exc:  # noqa: BLE001 — poster is best-effort; clip stays ready
        meta["clip_poster_error"] = str(exc)[:240]
        asset.asset_metadata = meta


async def maybe_auto_persist_asset(asset: VideoAsset, settings: Settings) -> None:
    if asset.status != "ready":
        return
    if not asset.storage_url and asset.provider_url:
        try:
            storage_url = await persist_provider_media(asset, settings)
        except MediaStoreError as exc:
            asset.error_message = f"Ready, but auto-persist failed: {exc}"
            asset.asset_metadata = {**dict(asset.asset_metadata or {}), "auto_persist_error": str(exc)}
            # Still try a poster from the provider URL when possible.
            maybe_attach_clip_poster(asset, settings)
            return
        asset.storage_url = storage_url
        asset.error_message = None
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "persisted": True,
            "auto_persisted": True,
            "storage_backend": "r2" if r2_enabled(settings) else "local",
        }
    if asset.asset_type == "video" and (asset.storage_url or asset.provider_url):
        maybe_attach_clip_poster(asset, settings)
        # New ready clips must be progressive-streamable for iOS.
        ensure_asset_streamable(asset, settings)


def ensure_asset_streamable(asset: VideoAsset, settings: Settings) -> bool:
    """Ensure ready video is stored with moov-at-start for iOS progressive play.

    Returns True when the asset is streamable (already was, or remux succeeded).
    Idempotent via ``asset_metadata.faststart``. Safe to call on clip detail GET.
    """
    if asset.asset_type != "video" or asset.status != "ready":
        return False
    meta = dict(asset.asset_metadata or {})
    if meta.get("faststart") is True:
        return True

    source = asset.storage_url or asset.provider_url
    if not source:
        return False

    try:
        path = ensure_local_media(str(source), settings)
    except MediaStoreError as exc:
        meta["faststart_error"] = f"load: {exc}"[:300]
        asset.asset_metadata = meta
        return False

    try:
        if mp4_has_faststart(path):
            meta["faststart"] = True
            meta.pop("faststart_error", None)
            asset.asset_metadata = meta
            return True
        fast_path = remux_mp4_faststart(path)
        # Keep stable name so signed URLs stay on the same key when possible.
        filename = f"{asset.id}.mp4"
        subdir = "play"
        storage_url = store_file(
            path=fast_path,
            subdir=subdir,
            filename=filename,
            settings=settings,
            content_type="video/mp4",
        )
        asset.storage_url = storage_url
        meta["faststart"] = True
        meta["faststart_remuxed"] = True
        meta.pop("faststart_error", None)
        asset.asset_metadata = meta
        return True
    except (VideoRenderError, MediaStoreError, OSError) as exc:
        meta["faststart_error"] = str(exc)[:300]
        asset.asset_metadata = meta
        return False


def provider_status(
    name: str, configured: bool, model: str | None, ready_message: str, missing_message: str
) -> VideoProviderStatusDto:
    return VideoProviderStatusDto(
        provider=name,
        configured=configured,
        model=model,
        status="ready" if configured else "needs_configuration",
        message=ready_message if configured else missing_message,
    )
