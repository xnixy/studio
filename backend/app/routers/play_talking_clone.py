"""Talking: ElevenLabs TTS, then Seedance mouths from those files. No Sync."""
from __future__ import annotations

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuditEvent, User, VideoAsset, VideoProject
from app.provider_errors import http_provider_exception
from app.routers.play_helpers import map_generation
from app.routers.play_video_generate import generate_play_video
from app.routers.play_voice_drive import clip_duration_from_audio, store_tts_public
from app.routers.play_voices import ResolvedTtsVoice, synthesize_resolved_tts_mp3
from app.schemas.play import PlayGenerateRequest, PlayGenerateResponse
from app.stock_voices import DEFAULT_STOCK_VOICE_ID
from app.voiceover import VoiceoverProviderError, expand_spoken_domains
from app.play_billing import release_if_reserved
from app.workspace_access import reserve_usage_committed

log = logging.getLogger(__name__)


async def generate_talking_clone(
    *,
    session: AsyncSession,
    settings: Settings,
    user: User,
    body: PlayGenerateRequest,
    project: VideoProject,
    play_model,
    prompt: str,
    aspect_ratio: str,
    resolved: ResolvedTtsVoice,
) -> PlayGenerateResponse:
    from app.routers.play_video_helpers import split_avatar_user_prompt

    spoken, _scene = split_avatar_user_prompt(prompt)
    spoken = expand_spoken_domains((spoken or "").strip())
    if not spoken:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Write the spoken line first. Assist can draft it.",
        )
    if not body.face_asset_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add a face before generating.",
        )
    if not settings.seedance_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Seedance API key is not configured",
        )
    if resolved.provider == "elevenlabs" and not settings.elevenlabs_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ElevenLabs API key is not configured",
        )

    try:
        tts_bytes = await synthesize_resolved_tts_mp3(
            resolved=resolved, script=spoken, settings=settings
        )
    except VoiceoverProviderError as exc:
        raise http_provider_exception(exc, kind="voice") from exc

    public_audio, audio_storage, measured = await store_tts_public(
        tts_bytes=tts_bytes,
        settings=settings,
        workspace_id=str(body.workspace_id),
        stem=f"talk-{resolved.provider_voice_id[:8]}",
    )
    max_seconds = int(play_model.max_duration_seconds or 15)
    if measured > max_seconds + 0.5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"That line is about {measured:.0f}s of speech. This take "
                f"is {max_seconds}s. Trim the line or Extend after."
            ),
        )
    duration_seconds = clip_duration_from_audio(measured, max_seconds=max_seconds)
    tts_seconds = max(5, duration_seconds)

    tts_reservation = None
    if resolved.is_clone:
        try:
            tts_reservation = await reserve_usage_committed(
                session,
                body.workspace_id,
                user.id,
                "voiceover_seconds",
                tts_seconds,
                {"operation": "play_talking_clone_tts"},
            )
        except Exception:
            raise

    seedance_body = body.model_copy(update={"duration_seconds": duration_seconds, "voice": None})
    try:
        response = await generate_play_video(
            session=session,
            settings=settings,
            user=user,
            body=seedance_body,
            project=project,
            play_model=play_model,
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            voice_audio_urls=[public_audio],
            voice_audio_speakers=["face"],
            extra_usage_event_ids=(
                [str(tts_reservation.id)] if tts_reservation is not None else None
            ),
        )
    except Exception:
        await release_if_reserved(session, tts_reservation)
        raise

    asset = await session.get(VideoAsset, response.generation.id)
    if asset is None:
        await release_if_reserved(session, tts_reservation)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Talking clip did not start.",
        )

    meta = dict(asset.asset_metadata or {})
    usage_ids = [str(i) for i in (meta.get("usage_event_ids") or []) if i]
    if tts_reservation is not None:
        sid = str(tts_reservation.id)
        if sid not in usage_ids:
            usage_ids.append(sid)
        row = await session.get(type(tts_reservation), tts_reservation.id)
        if row is not None and row.status == "reserved":
            row.status = "consumed"
    meta.update(
        {
            "play_mode": "avatar",
            "clone_audio_url": public_audio,
            "clone_audio_storage_url": audio_storage,
            "workspace_voice_id": str(resolved.workspace_voice_id) if resolved.workspace_voice_id else None,
            "voice": str(resolved.workspace_voice_id or body.voice or DEFAULT_STOCK_VOICE_ID),
            "provider_voice_id": resolved.provider_voice_id,
            "tts_provider": resolved.provider,
            "usage_event_ids": usage_ids,
            "extendable": True,
            "duration_seconds": duration_seconds,
        }
    )
    asset.asset_metadata = meta
    session.add(
        AuditEvent(
            workspace_id=body.workspace_id,
            actor_id=user.id,
            action="play.talking_clone_started" if resolved.is_clone else "play.talking_stock_started",
            details={"asset_id": str(asset.id), "cloned": resolved.is_clone},
        )
    )
    await session.commit()
    await session.refresh(asset)
    dto = map_generation(asset, settings)
    return PlayGenerateResponse(
        generation=dto,
        generations=[dto],
        message="Making the clip.",
    )


async def continue_talking_clone_voice_pass(
    session: AsyncSession,
    asset: VideoAsset,
    settings: Settings,
) -> bool:
    """In-flight Sync jobs still finish. New generates never set voice_pass."""
    meta = dict(asset.asset_metadata or {})
    if meta.get("voice_pass") != "pending":
        return False
    from app.media_store import (
        MediaStoreError,
        assert_media_reachable,
        download_media_url,
        public_media_url,
    )
    from app.provider_errors import public_error_message
    from app.sync_labs import SyncLabsError, create_sync_labs_video_dub

    grok_url = (asset.provider_url or "").strip()
    audio_url = str(meta.get("clone_audio_url") or "").strip()
    if not grok_url or not audio_url:
        asset.status = "failed"
        asset.error_message = "Clip is missing video or audio for the voice pass."
        meta["voice_pass"] = "failed"
        asset.asset_metadata = meta
        return False

    try:
        _path, grok_stored = await download_media_url(
            url=grok_url,
            settings=settings,
            subdir="video-assets",
            stem=f"{asset.id}-grok",
            fallback_extension=".mp4",
            max_bytes=250 * 1024 * 1024,
        )
        public_video = await assert_media_reachable(
            public_media_url(grok_stored, settings), settings, label="Source video"
        )
        public_audio = await assert_media_reachable(audio_url, settings, label="Clone audio")
        job = await create_sync_labs_video_dub(
            video_url=public_video,
            audio_url=public_audio,
            settings=settings,
            output_name=f"play-talk-{asset.id.hex[:12]}",
        )
    except (MediaStoreError, SyncLabsError, Exception) as exc:
        log.warning("talking clone voice pass failed asset=%s: %s", asset.id, exc)
        asset.status = "failed"
        asset.error_message = public_error_message(exc, kind="media")
        meta["voice_pass"] = "failed"
        meta["grok_source_url"] = grok_url
        asset.asset_metadata = meta
        return False

    request_id = getattr(job, "request_id", None) or getattr(job, "id", None)
    meta["voice_pass"] = "sync"
    meta["grok_request_id"] = asset.provider_request_id
    meta["grok_video_url"] = grok_stored
    meta["grok_source_url"] = grok_url
    raw = getattr(job, "raw", None)
    if isinstance(raw, dict):
        meta["sync_submit"] = raw
    asset.asset_metadata = meta
    asset.provider = "sync_labs"
    asset.source = "sync_labs"
    asset.provider_model = settings.sync_labs_model
    asset.provider_request_id = str(request_id) if request_id else None
    asset.provider_url = None
    asset.status = "processing"
    asset.error_message = None
    return True
