"""Play multi-ref materials: upload and list image/video/audio for Seedance."""
from __future__ import annotations

import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.media_store import MediaStoreError, r2_enabled, safe_media_name, store_bytes
from app.models import AuditEvent, User, VideoAsset
from app.provider_errors import http_provider_exception
from app.routers.play_helpers import get_or_create_play_project, is_play_ref_asset, map_play_ref
from app.routers.video_scene_plan import sniff_avatar_image
from app.schemas.play import PlayRefDto
from app.sync_labs import absolute_media_url
from app.workspace_access import require_permission

router = APIRouter(tags=["play"])

IMAGE_MAX = 20 * 1024 * 1024
VIDEO_MAX = 50 * 1024 * 1024
AUDIO_MAX = 20 * 1024 * 1024


def _sniff_play_ref(
    content: bytes,
    content_type: str | None,
    filename: str | None,
    kind_hint: str | None,
) -> tuple[str, str, str]:
    """Return (asset_type, content_type, extension)."""
    hint = (kind_hint or "").strip().lower()
    name = (filename or "").lower()
    ct = (content_type or "").split(";")[0].strip().lower()
    head = content[:16]

    # Try image first via existing sniffer
    try:
        img_ct, img_ext = sniff_avatar_image(content, content_type, filename)
        if img_ext not in (".heic", ".heif"):
            return "image", img_ct, img_ext
        raise ValueError("heic")
    except ValueError:
        pass

    # MP4 / MOV (ftyp)
    if len(head) >= 8 and head[4:8] == b"ftyp":
        if name.endswith(".mov") or ct in {"video/quicktime"}:
            return "video", "video/quicktime", ".mov"
        return "video", "video/mp4", ".mp4"
    if ct.startswith("video/") or name.endswith((".mp4", ".mov", ".m4v", ".webm")):
        if name.endswith(".mov") or ct == "video/quicktime":
            return "video", "video/quicktime", ".mov"
        if name.endswith(".webm") or ct == "video/webm":
            return "video", "video/webm", ".webm"
        return "video", "video/mp4", ".mp4"

    # Audio
    if ct.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".aac", ".ogg")):
        if name.endswith(".wav") or ct in {"audio/wav", "audio/x-wav", "audio/wave"}:
            return "audio", "audio/wav", ".wav"
        if name.endswith(".m4a") or ct in {"audio/mp4", "audio/m4a", "audio/x-m4a"}:
            return "audio", "audio/mp4", ".m4a"
        return "audio", "audio/mpeg", ".mp3"

    # ID3 mp3
    if head[:3] == b"ID3" or (len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "audio", "audio/mpeg", ".mp3"

    if hint in ("image", "video", "audio"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not read that {hint} file. Try another format.",
        )
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Use a JPEG/PNG/WebP image, MP4/MOV video, or MP3/WAV audio.",
    )


@router.post("/refs", response_model=PlayRefDto, status_code=status.HTTP_201_CREATED)
async def upload_play_ref(
    workspace_id: UUID = Form(...),
    file: UploadFile = File(...),
    kind: str | None = Form(None),
    label: str | None = Form(None, max_length=120),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayRefDto:
    await require_permission(session, workspace_id, user, "projects.write")
    # Read up to video max + 1
    content = await file.read(VIDEO_MAX + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty file")

    try:
        asset_type, content_type, extension = _sniff_play_ref(
            content, file.content_type, file.filename, kind
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read that file. Try another format.",
        ) from exc

    if extension in (".heic", ".heif"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="HEIC is not supported. Convert to JPEG first (the app does this for photos).",
        )

    max_bytes = IMAGE_MAX if asset_type == "image" else VIDEO_MAX if asset_type == "video" else AUDIO_MAX
    if len(content) > max_bytes:
        mb = max_bytes // (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"{asset_type.capitalize()} must be {mb} MB or smaller",
        )

    project = await get_or_create_play_project(
        session, workspace_id=workspace_id, user=user, platform_key="tiktok"
    )
    filename = f"{safe_media_name(project.id)}-{uuid.uuid4().hex[:10]}{extension}"
    try:
        storage_url = store_bytes(
            content=content,
            subdir="play-refs",
            filename=filename,
            settings=settings,
            content_type=content_type,
        )
    except MediaStoreError as exc:
        raise http_provider_exception(exc, kind="media") from exc

    display = (label or "").strip()
    if not display and file.filename:
        display = str(file.filename).rsplit(".", 1)[0].strip()[:80]
    if not display:
        display = f"{asset_type.capitalize()} ref"

    asset = VideoAsset(
        workspace_id=workspace_id,
        video_project_id=project.id,
        video_scene_id=None,
        asset_type=asset_type,
        source="upload",
        status="ready",
        prompt=f"Play ref ({asset_type})",
        provider="user_upload",
        storage_url=storage_url,
        asset_metadata={
            "play": True,
            "play_ref": True,
            "ref_kind": asset_type,
            "label": display,
            "original_filename": file.filename,
            "content_type": content_type,
            "public_url": absolute_media_url(storage_url, settings),
            "storage_backend": "r2" if r2_enabled(settings) else "local",
        },
    )
    session.add(asset)
    session.add(
        AuditEvent(
            workspace_id=workspace_id,
            actor_id=user.id,
            action="play.ref_uploaded",
            details={"asset_id": str(asset.id), "kind": asset_type},
        )
    )
    await session.commit()
    await session.refresh(asset)
    return map_play_ref(asset, settings)


@router.get("/refs", response_model=list[PlayRefDto])
async def list_play_refs(
    workspace_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    limit: int = Query(40, ge=1, le=100),
) -> list[PlayRefDto]:
    await require_permission(session, workspace_id, user, "projects.read")
    rows = (
        await session.scalars(
            select(VideoAsset)
            .where(
                VideoAsset.workspace_id == workspace_id,
                VideoAsset.status == "ready",
            )
            .order_by(VideoAsset.created_at.desc())
            .limit(200)
        )
    ).all()
    refs = [map_play_ref(a, settings) for a in rows if is_play_ref_asset(a)]
    return refs[:limit]
