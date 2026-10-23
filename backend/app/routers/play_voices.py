"""Play voice listing, preview, clone upload, and delete."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audio_upload import (
    MAX_CUSTOM_VOICE_UPLOAD_BYTES,
    prepare_clone_audio_for_provider,
    sniff_audio_upload,
    validate_clone_sample,
)
from app.clone_languages import normalize_clone_language, preview_script_for
from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.elevenlabs_voices import (
    ElevenLabsVoiceError,
    create_instant_voice_clone,
    delete_elevenlabs_voice,
    synthesize_elevenlabs_tts_mp3_bytes,
)
from app.models import User, VideoAsset, WorkspaceVoice
from app.models.base import utcnow
from app.provider_errors import http_provider_exception
from app.rate_limit_deps import enforce_rate_limit
from app.schemas.voices import (
    CustomVoicesAccessDto,
    PlayVoiceOptionDto,
    PlayVoicesResponse,
    VoicePreviewRequest,
    WorkspaceVoiceDto,
)
from app.stock_voices import (
    DEFAULT_STOCK_VOICE_ID,
    builtin_voice_rows,
    elevenlabs_voice_id_for,
    is_stock_voice_id,
    stock_voice_id_for,
    stock_voice_meta,
)
from app.voiceover import (
    VOICE_PREVIEW_SCRIPT,
    VoiceoverProviderError,
    synthesize_xai_tts_mp3_bytes,
)
from app.workspace_access import get_subscription, require_permission
from app.xai_custom_voices import XaiCustomVoiceError, delete_custom_voice

router = APIRouter(tags=["play"])
log = logging.getLogger(__name__)

PREVIEW_RATE_LIMIT = 20
PREVIEW_RATE_WINDOW_SECONDS = 60
PREVIEW_TEXT_MAX_CHARS = 160
DEFAULT_CLONE_CAP = 1
ALLOWED_GENDERS = frozenset({"female", "male", "neutral"})


@dataclass(slots=True)
class ResolvedTtsVoice:
    """Stock ElevenLabs id or a workspace clone (ElevenLabs or leftover xAI)."""

    provider_voice_id: str
    workspace_voice_id: UUID | None
    provider: str
    gender: str | None
    language: str | None
    is_clone: bool


def clone_cap_for_workspace(subscription) -> int:
    """Default 1 clone per workspace. Admin may raise via clone_slot_limit."""
    overrides = dict(getattr(subscription, "limit_overrides", None) or {})
    raw = overrides.get("clone_slot_limit")
    if raw is not None:
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            pass
    return DEFAULT_CLONE_CAP


def custom_voices_access(*, clone_cap: int, clone_count: int) -> CustomVoicesAccessDto:
    cap = max(0, int(clone_cap))
    count = max(0, int(clone_count))
    return CustomVoicesAccessDto(
        can_clone=count < cap,
        clone_cap=cap,
        clone_count=count,
    )


def standin_voice_id(gender: str | None, settings: Settings) -> str:
    """Grok-safe built-in. Never an ElevenLabs id."""
    g = (gender or "").strip().lower()
    if g == "male":
        return (settings.xai_tts_male_voice_id or "rex").strip() or "rex"
    return (settings.xai_tts_female_voice_id or "ara").strip() or "ara"


def grok_safe_voice_id(resolved: ResolvedTtsVoice, settings: Settings) -> str:
    """Voice id allowed in Grok reference_audios. Never an ElevenLabs id."""
    if resolved.is_clone or resolved.provider == "elevenlabs":
        return standin_voice_id(resolved.gender, settings)
    return (resolved.provider_voice_id or standin_voice_id(resolved.gender, settings)).strip()


def map_workspace_voice(row: WorkspaceVoice) -> WorkspaceVoiceDto:
    return WorkspaceVoiceDto(
        id=row.id,
        workspace_id=row.workspace_id,
        label=row.label,
        provider=row.provider,
        provider_voice_id=row.provider_voice_id,
        source="cloned",
        consent_name=row.consent_name,
        status=row.status,  # type: ignore[arg-type]
        gender=row.gender,
        language=row.language,
        is_default=bool(row.is_default),
        created_by_id=row.created_by_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _cloned_voice_option(row: WorkspaceVoice) -> PlayVoiceOptionDto:
    return PlayVoiceOptionDto(
        id=str(row.id),
        name=row.label,
        description="Your voice",
        provider=row.provider or "elevenlabs",
        source="cloned",
        available=row.status == "ready",
        provider_voice_id=row.provider_voice_id,
        workspace_voice_id=row.id,
        is_default=bool(row.is_default),
        gender=row.gender,
        language=row.language,
    )


async def _ready_clone_count(session: AsyncSession, workspace_id: UUID) -> int:
    total = await session.scalar(
        select(func.count())
        .select_from(WorkspaceVoice)
        .where(
            WorkspaceVoice.workspace_id == workspace_id,
            WorkspaceVoice.status == "ready",
        )
    )
    return int(total or 0)


async def _list_ready_clones(session: AsyncSession, workspace_id: UUID) -> list[WorkspaceVoice]:
    rows = (
        await session.scalars(
            select(WorkspaceVoice)
            .where(
                WorkspaceVoice.workspace_id == workspace_id,
                WorkspaceVoice.status == "ready",
            )
            .order_by(WorkspaceVoice.is_default.desc(), WorkspaceVoice.created_at.desc())
        )
    ).all()
    return list(rows)


def classify_face_bind_voice_id(raw: str | None) -> tuple[str, str | None]:
    """How a PATCH /faces/{id}/voice value should be stored.

    Returns ``("none", None)`` to clear, ``("stock", "jessica")`` for built-ins,
    or ``("clone", uuid)`` for a workspace clone. Raises ``ValueError`` if the
    token is neither a stock id nor a UUID.
    """
    text = (raw or "").strip()
    if not text:
        return ("none", None)
    if is_stock_voice_id(text):
        return ("stock", stock_voice_id_for(text))
    try:
        return ("clone", str(UUID(text)))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("That voice is not available.") from exc


async def resolve_face_bind_voice_id(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    bound_voice_id: str | None,
) -> str | None:
    """Canonical stock id or a ready clone UUID. None clears the bind."""
    try:
        kind, token = classify_face_bind_voice_id(bound_voice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That voice is not available.",
        ) from None
    if kind == "none" or not token:
        return None
    if kind == "stock":
        return token
    voice = await session.get(WorkspaceVoice, UUID(token))
    if voice is None or voice.workspace_id != workspace_id or voice.status != "ready":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That cloned voice is not in this workspace.",
        )
    return str(voice.id)


def play_voice_candidates(
    *,
    body_voice: str | None,
    face_bound_voice_id: str | None,
    honor_body_voice: bool = False,
) -> list[str]:
    """Bound voice, then the chip, then Jessica. Generate tries each until one resolves.

    Revoice and Extend honor an explicit Voice pick first. Bind still fills in
    when the request did not name a voice.
    """
    out: list[str] = []
    order = (
        (body_voice, face_bound_voice_id, DEFAULT_STOCK_VOICE_ID)
        if honor_body_voice
        else (face_bound_voice_id, body_voice, DEFAULT_STOCK_VOICE_ID)
    )
    for raw in order:
        text = (raw or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def pick_play_voice(
    *,
    body_voice: str | None,
    face_bound_voice_id: str | None,
    honor_body_voice: bool = False,
) -> str:
    """Preferred voice id: bound voice first, then the chip, then Jessica."""
    return play_voice_candidates(
        body_voice=body_voice,
        face_bound_voice_id=face_bound_voice_id,
        honor_body_voice=honor_body_voice,
    )[0]


def _face_bound_voice_id(face: VideoAsset | None, *, workspace_id: UUID) -> str | None:
    if face is None or face.workspace_id != workspace_id or face.asset_type != "image":
        return None
    from app.routers.play_helpers import is_face_asset

    if not is_face_asset(face):
        return None
    raw = (face.asset_metadata or {}).get("bound_voice_id")
    text = str(raw).strip() if raw else ""
    return text or None


async def resolve_play_generate_voice(
    *,
    session: AsyncSession,
    workspace_id: UUID,
    voice: str | None,
    face_asset_id: UUID | None,
    settings: Settings,
    honor_body_voice: bool = False,
) -> ResolvedTtsVoice:
    """Talking and voiced Scene: Face bound voice wins when a Face is on the clip.

    A deleted or unready bind must not 422 if the chip or Jessica still works.
    Revoice and Extend pass honor_body_voice so an explicit pick wins.
    """
    bound = None
    if face_asset_id is not None:
        face = await session.get(VideoAsset, face_asset_id)
        bound = _face_bound_voice_id(face, workspace_id=workspace_id)
    last_error: HTTPException | None = None
    for candidate in play_voice_candidates(
        body_voice=voice,
        face_bound_voice_id=bound,
        honor_body_voice=honor_body_voice,
    ):
        try:
            return await resolve_tts_voice(
                session=session,
                workspace_id=workspace_id,
                voice=candidate,
                settings=settings,
            )
        except HTTPException as exc:
            if exc.status_code != status.HTTP_422_UNPROCESSABLE_ENTITY:
                raise
            last_error = exc
    if last_error is not None:
        raise last_error
    return await resolve_tts_voice(
        session=session,
        workspace_id=workspace_id,
        voice=DEFAULT_STOCK_VOICE_ID,
        settings=settings,
    )


def _parse_uuid(value: str) -> UUID | None:
    try:
        return UUID(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None


async def resolve_tts_voice(
    *,
    session: AsyncSession,
    workspace_id: UUID,
    voice: str | None,
    settings: Settings,
) -> ResolvedTtsVoice:
    """Resolve body.voice to a TTS target. Clones never go to Grok as-is."""
    raw = (voice or DEFAULT_STOCK_VOICE_ID).strip() or DEFAULT_STOCK_VOICE_ID
    as_uuid = _parse_uuid(raw)
    if as_uuid is not None:
        row = await session.get(WorkspaceVoice, as_uuid)
        if row is None or row.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="That cloned voice is not in this workspace.",
            )
        if row.status != "ready":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="That cloned voice is not ready to use.",
            )
        provider_id = (row.provider_voice_id or "").strip()
        if not provider_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Cloned voice is missing a provider id.",
            )
        return ResolvedTtsVoice(
            provider_voice_id=provider_id,
            workspace_voice_id=row.id,
            provider=(row.provider or "elevenlabs").strip().lower() or "elevenlabs",
            gender=row.gender,
            language=row.language,
            is_clone=True,
        )

    stock_id = stock_voice_id_for(raw)
    meta = stock_voice_meta(stock_id)
    return ResolvedTtsVoice(
        provider_voice_id=elevenlabs_voice_id_for(stock_id),
        workspace_voice_id=None,
        provider="elevenlabs",
        gender=meta.get("gender") or None,
        language="en",
        is_clone=False,
    )


async def resolve_tts_voice_id(
    *,
    session: AsyncSession,
    workspace_id: UUID,
    voice: str | None,
    settings: Settings,
) -> tuple[str, UUID | None]:
    """Back-compat: (provider_voice_id, workspace_voice_id)."""
    resolved = await resolve_tts_voice(
        session=session, workspace_id=workspace_id, voice=voice, settings=settings
    )
    return resolved.provider_voice_id, resolved.workspace_voice_id


async def synthesize_resolved_tts_mp3(
    *,
    resolved: ResolvedTtsVoice,
    script: str,
    settings: Settings,
    timeout: float = 90,
) -> bytes:
    if resolved.provider == "elevenlabs":
        if not settings.elevenlabs_api_key:
            raise VoiceoverProviderError("ElevenLabs API key is not configured")
        return await synthesize_elevenlabs_tts_mp3_bytes(
            script=script,
            voice_id=resolved.provider_voice_id,
            settings=settings,
            language=resolved.language,
            timeout=timeout,
        )
    if not settings.xai_api_key:
        raise VoiceoverProviderError("xAI API key is not configured")
    return await synthesize_xai_tts_mp3_bytes(
        script=script,
        voice=resolved.provider_voice_id,
        settings=settings,
        timeout=timeout,
        language=resolved.language,
    )


async def _clear_face_voice_binds(
    session: AsyncSession, *, workspace_id: UUID, voice_id: UUID
) -> None:
    rows = (
        await session.scalars(
            select(VideoAsset).where(
                VideoAsset.workspace_id == workspace_id,
                VideoAsset.asset_type == "image",
                VideoAsset.asset_metadata["bound_voice_id"].astext == str(voice_id),
            )
        )
    ).all()
    for asset in rows:
        meta = dict(asset.asset_metadata or {})
        meta.pop("bound_voice_id", None)
        asset.asset_metadata = meta


async def _bind_voice_to_face(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    face_id: UUID,
    voice_id: UUID,
) -> None:
    face = await session.get(VideoAsset, face_id)
    if face is None or face.workspace_id != workspace_id or face.asset_type != "image":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That face is not in this workspace.",
        )
    meta = dict(face.asset_metadata or {})
    if not meta.get("face_library") and meta.get("mode") != "avatar_source_image":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="That asset is not a face.",
        )
    meta["bound_voice_id"] = str(voice_id)
    face.asset_metadata = meta


@router.get("/voices", response_model=PlayVoicesResponse)
async def list_play_voices(
    workspace_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayVoicesResponse:
    await require_permission(session, workspace_id, user, "projects.read")
    subscription = await get_subscription(session, workspace_id)
    clone_cap = clone_cap_for_workspace(subscription)
    clones = await _list_ready_clones(session, workspace_id)

    voices: list[PlayVoiceOptionDto] = [
        PlayVoiceOptionDto(
            id=row["id"],
            name=row["name"],
            description=row.get("description") or row["name"],
            provider="elevenlabs",
            source="builtin",
            available=True,
            provider_voice_id=row.get("elevenlabs_voice_id") or row["id"],
            gender=(row.get("gender") or None) or None,
            accent=(row.get("accent") or None) or None,
            language=(row.get("language") or None) or None,
        )
        for row in builtin_voice_rows()
    ]
    voices.extend(_cloned_voice_option(row) for row in clones)
    return PlayVoicesResponse(
        voices=voices,
        custom_voices_access=custom_voices_access(clone_cap=clone_cap, clone_count=len(clones)),
    )


@router.post("/voices/preview")
async def preview_play_voice(
    body: VoicePreviewRequest,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    await require_permission(session, body.workspace_id, user, "projects.read")
    await enforce_rate_limit(
        request,
        f"play.voice_preview:user:{user.id}",
        PREVIEW_RATE_LIMIT,
        PREVIEW_RATE_WINDOW_SECONDS,
        "Too many voice previews. Wait a minute and try again.",
    )

    voice_key = (body.voice or "").strip()
    if not voice_key:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Voice is required")

    resolved = await resolve_tts_voice(
        session=session,
        workspace_id=body.workspace_id,
        voice=voice_key,
        settings=settings,
    )
    text = (body.text or "").strip() or (
        preview_script_for(resolved.language) if resolved.is_clone else VOICE_PREVIEW_SCRIPT
    )
    if len(text) > PREVIEW_TEXT_MAX_CHARS:
        text = text[:PREVIEW_TEXT_MAX_CHARS].rstrip()

    try:
        audio = await synthesize_resolved_tts_mp3(
            resolved=resolved, script=text, settings=settings, timeout=75
        )
    except VoiceoverProviderError as exc:
        raise http_provider_exception(exc, kind="voice") from exc

    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={
            "Cache-Control": "private, max-age=300",
            "Content-Disposition": f'inline; filename="preview-{resolved.provider_voice_id}.mp3"',
        },
    )


@router.post(
    "/voices/clone",
    response_model=PlayVoiceOptionDto,
    status_code=status.HTTP_201_CREATED,
)
async def clone_play_voice(
    workspace_id: UUID = Form(...),
    label: str = Form(..., min_length=1, max_length=120),
    consent_name: str = Form(..., min_length=2, max_length=120),
    consent_confirmed: bool = Form(False),
    gender: str = Form(...),
    language: str = Form("en"),
    bind_face_id: UUID | None = Form(default=None),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> PlayVoiceOptionDto:
    await require_permission(session, workspace_id, user, "projects.write")

    if not consent_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confirm you have rights to use this voice sample.",
        )
    consent = consent_name.strip()
    if len(consent) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter the name of the person on the recording.",
        )
    gender_key = (gender or "").strip().lower()
    if gender_key not in ALLOWED_GENDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Pick a gender for this voice (female, male, or neutral).",
        )
    try:
        lang = normalize_clone_language(language)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    subscription = await get_subscription(session, workspace_id)
    cap = clone_cap_for_workspace(subscription)
    ready_count = await _ready_clone_count(session, workspace_id)
    if cap <= 0 or ready_count >= cap:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You have one custom voice. Delete it to record a new one."
                if cap == 1
                else f"This workspace allows {cap} custom voices. Delete one to add another."
            ),
        )

    if not settings.elevenlabs_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Voice cloning is not configured",
        )

    content = await file.read(MAX_CUSTOM_VOICE_UPLOAD_BYTES + 1)
    if len(content) > MAX_CUSTOM_VOICE_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Voice sample must be 10 MB or smaller.",
        )
    try:
        _content_type, ext = sniff_audio_upload(content, file.content_type, file.filename)
        file_bytes, filename, content_type = prepare_clone_audio_for_provider(
            content, extension=ext
        )
        validate_clone_sample(
            file_bytes,
            extension=".wav" if filename.endswith(".wav") else ext,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    display = (label or "").strip()[:120] or "Your voice"
    if display.casefold() == consent.casefold():
        display = "Your voice"

    try:
        created = await create_instant_voice_clone(
            file_bytes=file_bytes,
            filename=filename,
            content_type=content_type,
            name=display,
            language=lang,
            gender=gender_key,
            settings=settings,
            description=f"Studio workspace clone ({consent})",
        )
    except ElevenLabsVoiceError as exc:
        code = exc.status_code or 502
        mapped = {
            400: status.HTTP_400_BAD_REQUEST,
            403: status.HTTP_403_FORBIDDEN,
            413: status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            422: status.HTTP_422_UNPROCESSABLE_ENTITY,
            503: status.HTTP_503_SERVICE_UNAVAILABLE,
        }.get(code, status.HTTP_502_BAD_GATEWAY)
        raise HTTPException(status_code=mapped, detail=str(exc)) from exc

    provider_voice_id = str(created.get("voice_id") or "").strip()
    if not provider_voice_id:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="ElevenLabs did not return a voice id.",
        )

    try:
        await synthesize_elevenlabs_tts_mp3_bytes(
            script=preview_script_for(lang),
            voice_id=provider_voice_id,
            settings=settings,
            language=lang,
        )
    except VoiceoverProviderError as exc:
        try:
            await delete_elevenlabs_voice(provider_voice_id, settings)
        except ElevenLabsVoiceError:
            log.warning("preview failed; could not delete ElevenLabs voice %s", provider_voice_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not preview that clone. Try a cleaner recording.",
        ) from exc

    row = WorkspaceVoice(
        workspace_id=workspace_id,
        label=display,
        provider="elevenlabs",
        provider_voice_id=provider_voice_id,
        source="cloned",
        consent_name=consent,
        status="ready",
        gender=gender_key,
        language=lang,
        is_default=ready_count == 0,
        created_by_id=user.id,
    )
    session.add(row)
    await session.flush()
    if bind_face_id is not None:
        await _bind_voice_to_face(
            session, workspace_id=workspace_id, face_id=bind_face_id, voice_id=row.id
        )
    await session.commit()
    await session.refresh(row)
    log.info(
        "workspace voice cloned workspace=%s voice=%s provider_id=%s",
        workspace_id,
        row.id,
        provider_voice_id,
    )
    return _cloned_voice_option(row)


@router.delete("/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_play_voice(
    voice_id: UUID,
    workspace_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    await require_permission(session, workspace_id, user, "projects.write")
    row = await session.get(WorkspaceVoice, voice_id)
    if row is None or row.workspace_id != workspace_id or row.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")

    provider_id = (row.provider_voice_id or "").strip()
    provider = (row.provider or "").strip().lower()
    if provider_id:
        try:
            if provider == "elevenlabs" and settings.elevenlabs_api_key:
                await delete_elevenlabs_voice(provider_id, settings)
            elif provider == "xai" and settings.xai_api_key:
                await delete_custom_voice(provider_id, settings)
        except (ElevenLabsVoiceError, XaiCustomVoiceError) as exc:
            log.warning(
                "provider delete custom voice failed voice=%s provider_id=%s: %s",
                row.id,
                provider_id,
                exc,
            )

    await _clear_face_voice_binds(session, workspace_id=workspace_id, voice_id=row.id)
    row.status = "deleted"
    row.is_default = False
    row.updated_at = utcnow()
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/voices/{voice_id}/default", response_model=WorkspaceVoiceDto)
async def set_default_play_voice(
    voice_id: UUID,
    workspace_id: UUID = Query(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> WorkspaceVoiceDto:
    await require_permission(session, workspace_id, user, "projects.write")
    row = await session.get(WorkspaceVoice, voice_id)
    if row is None or row.workspace_id != workspace_id or row.status != "ready":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voice not found")

    await session.execute(
        update(WorkspaceVoice)
        .where(
            WorkspaceVoice.workspace_id == workspace_id,
            WorkspaceVoice.status == "ready",
            WorkspaceVoice.id != row.id,
        )
        .values(is_default=False, updated_at=utcnow())
    )
    row.is_default = True
    row.updated_at = utcnow()
    await session.commit()
    await session.refresh(row)
    return map_workspace_voice(row)


def _builtin_voices() -> list[PlayVoiceOptionDto]:
    return [
        PlayVoiceOptionDto(
            id=row["id"],
            name=row["name"],
            description=row.get("description") or row["name"],
            provider="elevenlabs",
            source="builtin",
            available=True,
            provider_voice_id=row.get("elevenlabs_voice_id") or row["id"],
            gender=(row.get("gender") or None) or None,
            accent=(row.get("accent") or None) or None,
            language=(row.get("language") or None) or None,
        )
        for row in builtin_voice_rows()
    ]
