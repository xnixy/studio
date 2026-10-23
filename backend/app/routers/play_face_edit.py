"""Face edit (touch up / new look) and bind a voice to a face."""
from __future__ import annotations

import re
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.image_providers import (
    GeneratedImage,
    ImageProviderError,
    persist_generated_image,
    resolve_image_model,
)
from app.intimate_contact import intimate_contact_refusal
from app.media_store import MediaStoreError, assert_media_reachable, public_media_url, r2_enabled
from app.models import AuditEvent, User, VideoAsset
from app.play_pricing import compute_play_quote
from app.provider_errors import http_provider_exception, public_error_message
from app.routers.play_helpers import get_or_create_play_project, is_face_asset, map_face
from app.routers.play_voices import resolve_face_bind_voice_id
from app.routers.video_helpers import add_generation_cost
from app.schemas.play import PlayFaceBindVoiceRequest, PlayFaceDto, PlayFaceEditRequest
from app.play_billing import release_if_unsettled
from app.workspace_access import require_permission, reserve_usage_committed
from app.xai_media import XaiMediaError, edit_xai_image

router = APIRouter(tags=["play"])

FACE_EDIT_MODEL = "grok-imagine-image-2.0"

_IDENTITY_RE = re.compile(
    r"\b("
    r"different person|another person|someone else|new identity|"
    r"a second person|two people|crowd|stranger"
    r")\b",
    re.I,
)
_SCENE_RE = re.compile(
    r"\b("
    r"in tokyo|at night|on a beach|city street|full body|wide shot|"
    r"walking through|standing in|sitting in a cafe|on stage|"
    r"landscape|skyline|nightclub"
    r")\b",
    re.I,
)


def _reject_edit_instruction(instruction: str, *, kind: str) -> str | None:
    text = (instruction or "").strip()
    if not text:
        return "Describe the change first."
    if _IDENTITY_RE.search(text):
        return "Keep this person. Identity changes belong in a new generate, not Edit."
    if _SCENE_RE.search(text) or (kind == "touchup" and re.search(r"\bin\s+[A-Z][a-z]+", text)):
        return "Scene changes belong in a clip, not on the face plate."
    return None


_HAIR_RE = re.compile(
    r"\b("
    r"hair|hairstyle|haircut|bangs|fringe|ponytail|bun|braid|"
    r"tied-?back|updo|bald|beard|mustache|moustache|goatee|sideburns|"
    r"clean shave|shaved head"
    r")\b",
    re.I,
)


def face_edit_prompt(*, instruction: str, kind: str) -> str:
    """Surgical edit of the source plate. Not a new portrait generate."""
    change = instruction.strip()
    lock = (
        "Edit the source photo. Do not generate a new portrait or a different person. "
        "Same person, same crop. Keep eyes, nose, mouth, jaw, bone structure, skin, "
        "age, and expression. Change only what the request names."
    )
    if _HAIR_RE.search(change):
        lock += (
            " If hair or facial hair changes, restyle that only. "
            "Do not rebuild the face to fit the hair."
        )
    if kind == "look":
        return (
            f"{lock} Wardrobe, hair, makeup, or finish may change when requested. "
            f"Do not restyle light or background unless the request asks. "
            f"Request: {change}"
        )
    return (
        f"{lock} Same clothes, same pose. Only polish the plate as requested. "
        f"Do not restyle light or background unless the request asks. "
        f"Request: {change}"
    )


@router.post("/faces/{face_id}/edit", response_model=PlayFaceDto)
async def edit_play_face(
    face_id: UUID,
    body: PlayFaceEditRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayFaceDto:
    await require_permission(session, body.workspace_id, user, "projects.write")
    instruction = (body.instruction or "").strip()
    kind = (body.kind or "touchup").strip().lower()
    if kind not in {"touchup", "look"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Kind must be touchup or look.")
    rejected = _reject_edit_instruction(instruction, kind=kind)
    if rejected:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=rejected)
    refused = intimate_contact_refusal(instruction)
    if refused:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=refused)

    face = await session.get(VideoAsset, face_id)
    if (
        face is None
        or face.workspace_id != body.workspace_id
        or face.asset_type != "image"
        or not is_face_asset(face)
        or face.status != "ready"
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face not found")

    source = face.storage_url or face.provider_url
    if not source:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This face has no image to edit.",
        )

    model_key = (body.model or "").strip() or None
    play_model = resolve_image_model(model_key, settings)
    if (play_model.provider or "xai").lower() != "xai":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Face edit uses Grok Image. Pick a Grok still model.",
        )
    edit_model = FACE_EDIT_MODEL if not (model_key or "").startswith("grok-imagine-image") else (
        play_model.provider_model or FACE_EDIT_MODEL
    )
    if model_key and play_model.provider_model and play_model.provider_model.startswith("grok-imagine-image"):
        # Catalog stills are generate-only quality/fast. Edits pin 2.0 unless they
        # already named an imagine-image-2 model.
        if "2.0" in play_model.provider_model or play_model.provider_model.endswith("-2"):
            edit_model = play_model.provider_model
        else:
            edit_model = FACE_EDIT_MODEL

    quote = compute_play_quote(mode="image", model_id=model_key or play_model.id, face_generate=True)
    tokens = max(1, int(quote.per_item))
    reservation = await reserve_usage_committed(
        session,
        body.workspace_id,
        user.id,
        quote.meter,
        tokens,
        {"operation": "play_face_edit", "kind": kind, "token_cost": tokens, "quote": quote.as_dict()},
    )

    try:
        public_source = await assert_media_reachable(
            public_media_url(str(source), settings), settings, label="Face plate"
        )
        result = await edit_xai_image(
            prompt=face_edit_prompt(instruction=instruction, kind=kind),
            image_url=public_source,
            settings=settings,
            model=edit_model,
            resolution="1k",
        )
        generated = GeneratedImage(
            provider="xai",
            model=result.model or edit_model,
            model_id=play_model.id,
            url=result.url,
            content=None,
            mime_type=None,
            cost_usd_ticks=result.cost_usd_ticks,
            raw=result.raw,
        )
        stored_url = await persist_generated_image(
            result=generated,
            settings=settings,
            subdir="avatar-assets",
            stem=uuid.uuid4(),
        )
    except (XaiMediaError, ImageProviderError, MediaStoreError) as exc:
        await release_if_unsettled(session, type(reservation), reservation.id)
        raise http_provider_exception(exc, kind="media") from exc
    except Exception:
        await release_if_unsettled(session, type(reservation), reservation.id)
        raise

    save = "new" if kind == "look" else ((body.save or "replace").strip().lower() or "replace")
    src_meta = dict(face.asset_metadata or {})
    if save == "new":
        project = await get_or_create_play_project(
            session, workspace_id=body.workspace_id, user=user, platform_key="tiktok"
        )
        sibling = VideoAsset(
            workspace_id=body.workspace_id,
            video_project_id=project.id,
            video_scene_id=None,
            asset_type="image",
            source="xai",
            status="ready",
            prompt=instruction,
            provider="xai",
            provider_model=edit_model,
            storage_url=stored_url,
            provider_url=result.url,
            cost_usd_ticks=result.cost_usd_ticks,
            asset_metadata={
                "play": True,
                "play_mode": "avatar",
                "mode": "avatar_source_image",
                "face_library": True,
                "source_kind": "edit",
                "label": src_meta.get("label") or face.prompt or "Look",
                "consent_confirmed": src_meta.get("consent_confirmed", True),
                "consent_name": src_meta.get("consent_name"),
                "consent_user_id": src_meta.get("consent_user_id"),
                "parent_face_id": str(face.id),
                "previous_url": source,
                "bound_voice_id": src_meta.get("bound_voice_id"),
                "public_url": public_media_url(stored_url, settings),
                "storage_backend": "r2" if r2_enabled(settings) else "local",
                "edit_kind": kind,
                "edit_instruction": instruction,
            },
        )
        session.add(sibling)
        target = sibling
    else:
        previous = face.storage_url or face.provider_url
        src_meta["previous_url"] = previous
        src_meta["edit_kind"] = kind
        src_meta["edit_instruction"] = instruction
        face.storage_url = stored_url
        face.provider_url = result.url
        face.provider_model = edit_model
        face.cost_usd_ticks = result.cost_usd_ticks
        face.prompt = instruction
        face.asset_metadata = src_meta
        target = face

    stored = await session.get(type(reservation), reservation.id)
    if stored is not None:
        stored.status = "consumed"
    if result.cost_usd_ticks:
        add_generation_cost(
            session,
            workspace_id=body.workspace_id,
            user_id=user.id,
            feature="play_face_edit",
            provider_model=edit_model,
            provider_request_id=None,
            cost_usd_ticks=result.cost_usd_ticks,
            metadata={"face_id": str(target.id), "kind": kind},
        )
    session.add(
        AuditEvent(
            workspace_id=body.workspace_id,
            actor_id=user.id,
            action="play.face_edited",
            details={"face_id": str(target.id), "kind": kind, "save": save},
        )
    )
    await session.commit()
    await session.refresh(target)
    return map_face(target, settings)


@router.patch("/faces/{face_id}/voice", response_model=PlayFaceDto)
async def bind_play_face_voice(
    face_id: UUID,
    body: PlayFaceBindVoiceRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayFaceDto:
    await require_permission(session, body.workspace_id, user, "projects.write")
    face = await session.get(VideoAsset, face_id)
    if (
        face is None
        or face.workspace_id != body.workspace_id
        or face.asset_type != "image"
        or not is_face_asset(face)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face not found")
    meta = dict(face.asset_metadata or {})
    bound = await resolve_face_bind_voice_id(
        session,
        workspace_id=body.workspace_id,
        bound_voice_id=body.bound_voice_id,
    )
    if bound is None:
        meta.pop("bound_voice_id", None)
    else:
        meta["bound_voice_id"] = bound
    face.asset_metadata = meta
    await session.commit()
    await session.refresh(face)
    return map_face(face, settings)


@router.post("/faces/{face_id}/restore", response_model=PlayFaceDto)
async def restore_play_face(
    face_id: UUID,
    body: PlayFaceBindVoiceRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayFaceDto:
    """One-step undo after a touch-up replace (swaps previous_url back)."""
    await require_permission(session, body.workspace_id, user, "projects.write")
    face = await session.get(VideoAsset, face_id)
    if (
        face is None
        or face.workspace_id != body.workspace_id
        or face.asset_type != "image"
        or not is_face_asset(face)
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Face not found")
    meta = dict(face.asset_metadata or {})
    previous = str(meta.get("previous_url") or "").strip()
    if not previous:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Nothing to undo on this face.",
        )
    current = face.storage_url or face.provider_url
    face.storage_url = previous
    meta["previous_url"] = current
    face.asset_metadata = meta
    await session.commit()
    await session.refresh(face)
    return map_face(face, settings)
