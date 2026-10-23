"""Workspace face library: list, upload, generate reusable avatar faces."""
from __future__ import annotations

import logging
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
from app.provider_errors import http_provider_exception, public_error_message
from app.routers.play_helpers import get_or_create_play_project, is_face_asset, map_face, map_generation
from app.routers.video_helpers import add_generation_cost
from app.routers.video_scene_plan import sniff_avatar_image
from app.image_providers import ImageProviderError, generate_image, persist_generated_image
from app.intimate_contact import intimate_contact_refusal
from app.schemas.play import (
    PlayFaceDto,
    PlayFaceGenerateRequest,
    PlayGenerationDto,
)
from app.sync_labs import absolute_media_url
from app.play_billing import release_if_unsettled
from app.workspace_access import require_permission, reserve_usage_committed

router = APIRouter(tags=["play"])
log = logging.getLogger(__name__)


def face_plate_prompt(prompt: str) -> str:
    """Build the image prompt for a generated face plate.

    Face + shoulders only. Keep the wording light so the model stays natural
    (heavy "identity plate / solid gray / seamless studio" phrasing looks synthetic).

    Deep focus is deliberate. Reference-to-video models inherit the plate's optics —
    lens, depth of field, lighting — along with the likeness, so bokeh baked in here
    comes back as a blurred background in every Talking clip made from this face,
    even when the scene text asks for a sharp one. Phrased positively because image
    models do not reliably honour "no blur".
    """
    return (
        f"Photorealistic portrait of {prompt.strip()}. "
        "Front-facing head and shoulders, clear face, natural skin texture, "
        "even soft lighting, deep depth of field with the whole frame in sharp focus, "
        "plain uncluttered background that stays in focus. "
        "No text, no watermark, no logo."
    )


@router.post("/avatar-image", response_model=PlayGenerationDto, status_code=status.HTTP_201_CREATED)
async def play_upload_avatar_image(
    workspace_id: UUID = Form(...),
    file: UploadFile = File(...),
    consent_confirmed: bool = Form(False),
    consent_name: str = Form(..., min_length=2, max_length=120),
    label: str | None = Form(None, max_length=120),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayGenerationDto:
    await require_permission(session, workspace_id, user, "projects.write")
    if not consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm you have rights to use this face",
        )
    content = await file.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Avatar image must be 20 MB or smaller",
        )
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty image file")

    try:
        content_type, extension = sniff_avatar_image(content, file.content_type, file.filename)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use a JPEG, PNG, or WebP photo. On iPhone, the app converts HEIC before upload.",
        ) from None

    if extension in (".heic", ".heif"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="HEIC is not supported on the server. Re-upload as JPEG (the iOS app should convert automatically).",
        )

    project = await get_or_create_play_project(
        session, workspace_id=workspace_id, user=user, platform_key="tiktok"
    )
    filename = f"{safe_media_name(project.id)}-{uuid.uuid4().hex[:10]}{extension}"
    try:
        storage_url = store_bytes(
            content=content,
            subdir="avatar-assets",
            filename=filename,
            settings=settings,
            content_type=content_type or "application/octet-stream",
        )
    except MediaStoreError as exc:
        raise http_provider_exception(exc, kind="media") from exc

    display = (label or "").strip()
    if not display and file.filename:
        display = str(file.filename).rsplit(".", 1)[0].strip()[:80]
    if not display:
        display = "Uploaded face"
    # Never store consent name as the display label
    if display.casefold() == consent_name.strip().casefold():
        display = "Uploaded face"

    asset = VideoAsset(
        workspace_id=workspace_id,
        video_project_id=project.id,
        video_scene_id=None,
        asset_type="image",
        source="upload",
        status="ready",
        prompt="Play avatar face upload",
        provider="user_upload",
        storage_url=storage_url,
        asset_metadata={
            "play": True,
            "play_mode": "avatar",
            "play_platform": "tiktok",
            "mode": "avatar_source_image",
            "face_library": True,
            "source_kind": "upload",
            "label": display,
            "consent_confirmed": True,
            "consent_name": consent_name.strip(),
            "consent_user_id": str(user.id),
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
            action="play.avatar_image_uploaded",
            details={"asset_id": str(asset.id)},
        )
    )
    await session.commit()
    await session.refresh(asset)
    return map_generation(asset, settings)


@router.get("/faces", response_model=list[PlayFaceDto])
async def list_play_faces(
    workspace_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    limit: int = Query(40, ge=1, le=100),
) -> list[PlayFaceDto]:
    """Workspace face library: uploaded or generated faces reusable for avatar / lip-sync."""
    await require_permission(session, workspace_id, user, "projects.read")
    rows = (
        await session.scalars(
            select(VideoAsset)
            .where(
                VideoAsset.workspace_id == workspace_id,
                VideoAsset.asset_type == "image",
                VideoAsset.status == "ready",
            )
            .order_by(VideoAsset.created_at.desc())
            .limit(200)
        )
    ).all()
    faces = [map_face(a, settings) for a in rows if is_face_asset(a)]
    return faces[:limit]


@router.post("/faces/generate", response_model=PlayFaceDto, status_code=status.HTTP_201_CREATED)
async def generate_play_face(
    body: PlayFaceGenerateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayFaceDto:
    """Generate a new face still and save it to the workspace face library (1 image credit)."""
    await require_permission(session, body.workspace_id, user, "projects.write")
    if not body.consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm you have rights to use this likeness or that it is not a real person you lack rights to",
        )

    prompt = body.prompt.strip()
    refused = intimate_contact_refusal(prompt)
    if refused:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=refused)
    consent_name = body.consent_name.strip()
    display = (body.label or "").strip()
    if not display:
        display = (prompt[:48] + "…") if len(prompt) > 48 else prompt
    if display.casefold() == consent_name.casefold():
        display = (prompt[:48] + "…") if len(prompt) > 48 else prompt
    enhanced = face_plate_prompt(prompt)

    project = await get_or_create_play_project(
        session, workspace_id=body.workspace_id, user=user, platform_key="tiktok"
    )
    model_key = (body.model or "").strip() or None
    from app.image_providers import ensure_image_provider_configured, resolve_image_model
    from app.plan_entitlements import require_play_model_for_workspace

    play_model = resolve_image_model(model_key, settings)
    try:
        ensure_image_provider_configured(play_model, settings)
    except ImageProviderError as exc:
        raise http_provider_exception(exc, kind="media") from exc
    await require_play_model_for_workspace(session, body.workspace_id, play_model)

    from app.play_pricing import compute_play_quote

    quote = compute_play_quote(mode="image", model_id=model_key, face_generate=True)
    tokens = max(1, int(quote.per_item))
    reservation = await reserve_usage_committed(
        session,
        body.workspace_id,
        user.id,
        quote.meter,
        tokens,
        {
            "operation": "play_face_generate",
            "model_id": model_key,
            "token_cost": tokens,
            "quote": quote.as_dict(),
        },
    )
    reservation_id = reservation.id
    asset = VideoAsset(
        workspace_id=body.workspace_id,
        video_project_id=project.id,
        video_scene_id=None,
        asset_type="image",
        source=play_model.provider,
        status="processing",
        prompt=prompt,
        provider=play_model.provider,
        asset_metadata={
            "play": True,
            "play_mode": "avatar",
            "mode": "avatar_source_image",
            "face_library": True,
            "source_kind": "generated",
            "label": display,
            "consent_confirmed": True,
            "consent_name": consent_name,
            "consent_user_id": str(user.id),
            "aspect_ratio": "1:1",
            "resolution": "1k",
            "model_id": model_key or play_model.id,
        },
    )
    session.add(asset)
    await session.flush()
    try:
        result = await generate_image(
            prompt=enhanced,
            aspect_ratio="1:1",
            resolution="1k",
            settings=settings,
            model=model_key,
        )
    except ImageProviderError as exc:
        asset.status = "failed"
        asset.error_message = public_error_message(exc, kind="media")
        await session.commit()
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise http_provider_exception(exc, kind="media") from exc
    except Exception:
        await release_if_unsettled(session, type(reservation), reservation_id)
        raise

    asset.status = "ready"
    asset.provider = result.provider
    asset.source = result.provider
    asset.provider_url = result.url
    asset.provider_model = result.model
    asset.cost_usd_ticks = result.cost_usd_ticks
    try:
        stored_url = await persist_generated_image(
            result=result, settings=settings, subdir="avatar-assets", stem=asset.id
        )
        asset.storage_url = stored_url
        if not asset.provider_url:
            asset.provider_url = stored_url
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "public_url": absolute_media_url(stored_url, settings),
            "storage_backend": "r2" if r2_enabled(settings) else "local",
            "model_id": result.model_id,
        }
    except Exception as persist_exc:  # noqa: BLE001
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "persist_error": str(persist_exc)[:240],
        }
    add_generation_cost(
        session,
        workspace_id=body.workspace_id,
        user_id=user.id,
        feature="play_face_generate",
        provider_model=result.model,
        provider_request_id=None,
        cost_usd_ticks=result.cost_usd_ticks,
        metadata={"asset_id": str(asset.id), "model_id": result.model_id},
    )
    stored_ok = await session.get(type(reservation), reservation_id)
    if stored_ok is not None:
        stored_ok.status = "consumed"
    session.add(
        AuditEvent(
            workspace_id=body.workspace_id,
            actor_id=user.id,
            action="play.face_generated",
            details={"asset_id": str(asset.id)},
        )
    )
    await session.commit()
    await session.refresh(asset)
    return map_face(asset, settings)


@router.delete("/faces/{face_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_play_face(
    face_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove a face from the workspace library."""
    asset = await session.get(VideoAsset, face_id)
    if asset is None or not is_face_asset(asset):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face not found")
    await require_permission(session, asset.workspace_id, user, "projects.write")
    session.add(
        AuditEvent(
            workspace_id=asset.workspace_id,
            actor_id=user.id,
            action="play.face_deleted",
            details={"asset_id": str(asset.id)},
        )
    )
    await session.delete(asset)
    await session.commit()
