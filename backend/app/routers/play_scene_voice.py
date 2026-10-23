"""A scene + Face: separate ElevenLabs takes, Seedance @Audio1/@Audio2. No Sync."""
from __future__ import annotations

import logging
import math
import subprocess
import tempfile
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuditEvent, User, VideoAsset, VideoProject
from app.provider_errors import http_provider_exception
from app.routers.play_helpers import map_generation
from app.routers.play_scene_dialogue import (
    SceneLine,
    ensure_other_speaker_gender,
    extract_scene_dialogue,
    normalize_scene_dialogue_order,
    other_speaker_gender,
)
from app.routers.play_video_generate import generate_play_video
from app.routers.play_voice_drive import clip_duration_from_audio, store_tts_public
from app.routers.play_voices import ResolvedTtsVoice, synthesize_resolved_tts_mp3
from app.schemas.play import PlayGenerateRequest, PlayGenerateResponse
from app.stock_voices import opposite_stock_voice_id
from app.video_renderer import ffmpeg_path
from app.voiceover import VoiceoverProviderError
from app.play_billing import release_if_reserved
from app.workspace_access import reserve_usage_committed

log = logging.getLogger(__name__)


def clone_voiceover_seconds(face_audio_seconds: float) -> int:
    """Clone voiceover for Face TTS only. Friend stock takes are not billed."""
    if face_audio_seconds <= 0:
        return 0
    return max(5, int(math.ceil(face_audio_seconds)))

_GAP_MS = 400


def concat_mp3_with_gaps(chunks: list[bytes], *, gap_ms: int = _GAP_MS) -> bytes:
    """Join one speaker's takes. Two-handers stay on separate files."""
    if not chunks:
        raise ValueError("No audio to mix")
    if len(chunks) == 1:
        return chunks[0]
    binary = ffmpeg_path()
    if not binary:
        raise VoiceoverProviderError("Audio mix needs ffmpeg")
    gap = max(0.05, min(1.5, gap_ms / 1000.0))
    n = len(chunks)
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        inputs: list[str] = []
        for index, data in enumerate(chunks):
            path = root / f"p{index}.mp3"
            path.write_bytes(data)
            inputs.extend(["-i", str(path)])
        parts: list[str] = []
        concat_in: list[str] = []
        for index in range(n):
            parts.append(f"[{index}:a]aformat=sample_rates=24000:channel_layouts=mono[a{index}]")
            concat_in.append(f"[a{index}]")
            if index < n - 1:
                parts.append(f"anullsrc=r=24000:cl=mono:d={gap:.3f}[s{index}]")
                concat_in.append(f"[s{index}]")
        count = 2 * n - 1
        filt = ";".join(parts) + ";" + "".join(concat_in) + f"concat=n={count}:v=0:a=1[out]"
        out = root / "out.mp3"
        cmd = [binary, "-y", *inputs, "-filter_complex", filt, "-map", "[out]", "-c:a", "libmp3lame", str(out)]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
        except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            raise VoiceoverProviderError("Could not mix the spoken lines.") from exc
        data = out.read_bytes()
        if not data:
            raise VoiceoverProviderError("Could not mix the spoken lines.")
        return data


async def _tts_files_for_lines(
    *,
    lines: list[SceneLine],
    face_voice: ResolvedTtsVoice,
    other_voice: ResolvedTtsVoice,
    settings: Settings,
    workspace_id: str,
) -> tuple[list[str], list[str], float, float]:
    """One MP3 per line in order. Face is @AudioN with speaker face; friend is other."""
    urls: list[str] = []
    speakers: list[str] = []
    total = 0.0
    face_seconds = 0.0
    for index, line in enumerate(lines):
        resolved = face_voice if line.speaker == "face" else other_voice
        chunk = await synthesize_resolved_tts_mp3(
            resolved=resolved, script=line.text, settings=settings
        )
        public, _storage, seconds = await store_tts_public(
            tts_bytes=chunk,
            settings=settings,
            workspace_id=workspace_id,
            stem=f"scene-{index}-{line.speaker}",
        )
        urls.append(public)
        speakers.append("face" if line.speaker == "face" else "other")
        total += seconds
        if line.speaker == "face":
            face_seconds += seconds
    return urls, speakers, total, face_seconds


async def generate_scene_voice(
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
    prompt = normalize_scene_dialogue_order(prompt)
    other_gender = other_speaker_gender(resolved.gender)
    prompt = ensure_other_speaker_gender(prompt, other_gender)
    lines = extract_scene_dialogue(prompt, face_gender=resolved.gender)
    if not lines:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Write the spoken line, or quote each speaker, so we know who says what.",
        )
    if not body.face_asset_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Add a face before using an exact voice on a scene.",
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

    other_id = opposite_stock_voice_id(resolved.gender)
    other_voice = await _resolve_other_stock(session, body.workspace_id, other_id, settings)

    from app.seedance_media import is_seedance_25

    audio_cap = 10 if is_seedance_25(play_model.provider_model or play_model.id) else 3
    if len(lines) > audio_cap:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"This take can hold {audio_cap} spoken lines. Trim a line or use 2.5.",
        )

    try:
        audio_urls, speakers, measured, face_seconds = await _tts_files_for_lines(
            lines=lines,
            face_voice=resolved,
            other_voice=other_voice,
            settings=settings,
            workspace_id=str(body.workspace_id),
        )
    except VoiceoverProviderError as exc:
        raise http_provider_exception(exc, kind="voice") from exc

    max_seconds = int(play_model.max_duration_seconds or 15)
    if measured > max_seconds + 0.5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Those lines are about {measured:.0f}s of speech. This take "
                f"is {max_seconds}s. Trim the lines or Extend after."
            ),
        )
    duration_seconds = clip_duration_from_audio(measured, max_seconds=max_seconds)
    tts_seconds = clone_voiceover_seconds(face_seconds)

    tts_reservation = None
    if resolved.is_clone and tts_seconds:
        try:
            tts_reservation = await reserve_usage_committed(
                session,
                body.workspace_id,
                user.id,
                "voiceover_seconds",
                tts_seconds,
                {"operation": "play_scene_voice_tts"},
            )
        except Exception:
            raise

    seedance_body = body.model_copy(
        update={"duration_seconds": duration_seconds, "voice": None, "count": 1}
    )
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
            voice_audio_urls=audio_urls,
            voice_audio_speakers=speakers,
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
            detail="Scene clip did not start.",
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
            "play_mode": "video",
            "clone_audio_url": audio_urls[0] if audio_urls else None,
            "voice_audio_urls": audio_urls,
            "workspace_voice_id": str(resolved.workspace_voice_id) if resolved.workspace_voice_id else None,
            "voice": str(resolved.workspace_voice_id or body.voice or ""),
            "other_voice": other_id,
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
            action="play.scene_voice_started" if resolved.is_clone else "play.scene_stock_voice_started",
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


async def _resolve_other_stock(
    session: AsyncSession,
    workspace_id: UUID,
    voice_id: str,
    settings: Settings,
) -> ResolvedTtsVoice:
    from app.routers.play_voices import resolve_tts_voice

    return await resolve_tts_voice(
        session=session,
        workspace_id=workspace_id,
        voice=voice_id,
        settings=settings,
    )
