"""ElevenLabs Instant Voice Clone + TTS.

New workspace clones go here. TTS is pay-per-character; clone slots are a
plan entitlement on the ElevenLabs account, not PAYG.
"""
from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.audio_upload import MAX_CUSTOM_VOICE_UPLOAD_BYTES
from app.config import Settings
from app.media_store import store_bytes
from app.voiceover import VoiceoverProviderError, safe_filename, voiceover_text

log = logging.getLogger(__name__)

ELEVENLABS_API_BASE = "https://api.elevenlabs.io"
# Clone TTS. Instant Voice Clone is model-agnostic at create time; speech after
# that (preview + Talking) uses v3. Do not pin multilingual v2 again.
ELEVENLABS_TTS_MODEL = "eleven_v3"
ELEVENLABS_TTS_OUTPUT_FORMAT = "mp3_44100_128"


class ElevenLabsVoiceError(RuntimeError):
    """Raised when the ElevenLabs voices/TTS API fails or is unavailable."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _auth_headers(settings: Settings, *, json_body: bool = False) -> dict[str, str]:
    if not settings.elevenlabs_api_key:
        raise ElevenLabsVoiceError("ElevenLabs API key is not configured", status_code=503)
    headers = {"xi-api-key": settings.elevenlabs_api_key}
    if json_body:
        headers["Content-Type"] = "application/json"
    return headers


def _friendly_error(status_code: int, body: str) -> ElevenLabsVoiceError:
    lowered = body.lower()
    if status_code in (401, 403):
        return ElevenLabsVoiceError(
            "ElevenLabs API key is missing, invalid, or cannot clone voices on this plan.",
            status_code=status_code,
        )
    if status_code == 400 and ("voice" in lowered and ("limit" in lowered or "slot" in lowered)):
        return ElevenLabsVoiceError(
            "Custom voice slots are full. Delete an unused clone and try again.",
            status_code=400,
        )
    if status_code == 400 and (
        "invalid_audio" in lowered or "corrupt" in lowered or "playable audio" in lowered
    ):
        return ElevenLabsVoiceError(
            "That recording could not be read. Record again in a quiet room, or upload a Voice Memos m4a.",
            status_code=400,
        )
    if status_code == 422:
        return ElevenLabsVoiceError(
            "ElevenLabs could not use that recording. Try a cleaner sample.",
            status_code=422,
        )
    snippet = body[:280] if body else "no body"
    return ElevenLabsVoiceError(
        f"ElevenLabs request failed with HTTP {status_code}: {snippet}",
        status_code=status_code,
    )


async def create_instant_voice_clone(
    *,
    file_bytes: bytes,
    filename: str,
    content_type: str | None,
    name: str,
    settings: Settings,
    language: str = "en",
    gender: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    """POST /v1/voices/add (IVC). Returns the voice object (includes voice_id)."""
    if not file_bytes:
        raise ElevenLabsVoiceError("Reference audio file is empty.", status_code=400)
    if len(file_bytes) > MAX_CUSTOM_VOICE_UPLOAD_BYTES:
        raise ElevenLabsVoiceError("Reference audio must be 10 MB or smaller.", status_code=413)

    labels: dict[str, str] = {}
    if language:
        labels["language"] = language.strip()[:16]
    if gender and gender.strip().lower() in {"female", "male", "neutral"}:
        labels["gender"] = gender.strip().lower()

    safe_name = (filename or "reference.wav").strip() or "reference.wav"
    mime = (content_type or "application/octet-stream").split(";")[0].strip() or "application/octet-stream"
    display = (name or "Cloned voice").strip()[:120] or "Cloned voice"
    form_data: dict[str, str] = {"name": display}
    if description and description.strip():
        form_data["description"] = description.strip()[:500]
    if labels:
        form_data["labels"] = json.dumps(labels)

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{ELEVENLABS_API_BASE}/v1/voices/add",
            headers=_auth_headers(settings),
            data=form_data,
            files={"files": (safe_name, file_bytes, mime)},
        )

    if response.status_code not in (200, 201):
        log.warning(
            "elevenlabs clone rejected status=%s name=%s mime=%s magic=%s body=%s",
            response.status_code,
            safe_name,
            mime,
            file_bytes[:12].hex(),
            response.text[:300],
        )
        raise _friendly_error(response.status_code, response.text[:500])
    try:
        data = response.json()
    except ValueError as exc:
        raise ElevenLabsVoiceError("ElevenLabs clone response was not JSON") from exc
    if not isinstance(data, dict):
        raise ElevenLabsVoiceError("ElevenLabs clone response JSON must be an object")
    voice_id = str(data.get("voice_id") or "").strip()
    if not voice_id:
        raise ElevenLabsVoiceError("ElevenLabs clone response missing voice_id")
    return data


async def delete_elevenlabs_voice(voice_id: str, settings: Settings) -> None:
    """DELETE /v1/voices/{voice_id}. Ignores 404 (already gone)."""
    key = (voice_id or "").strip()
    if not key:
        raise ElevenLabsVoiceError("voice_id is required", status_code=400)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.delete(
            f"{ELEVENLABS_API_BASE}/v1/voices/{key}",
            headers=_auth_headers(settings),
        )
    if response.status_code in (200, 204, 404):
        return
    raise _friendly_error(response.status_code, response.text[:500])


async def synthesize_elevenlabs_tts_mp3_bytes(
    *,
    script: str,
    voice_id: str,
    settings: Settings,
    language: str | None = None,
    timeout: float = 120,
) -> bytes:
    """Call ElevenLabs TTS and return raw MP3 bytes (no storage)."""
    if not settings.elevenlabs_api_key:
        raise VoiceoverProviderError("ElevenLabs API key is not configured")
    text = voiceover_text(str(script)).strip()
    if not text:
        raise VoiceoverProviderError("Script is empty")
    vid = (voice_id or "").strip()
    if not vid:
        raise VoiceoverProviderError("Voice id is required")

    payload: dict[str, Any] = {
        "text": text,
        "model_id": ELEVENLABS_TTS_MODEL,
    }
    # v3 honors language_code (ISO 639-1, plus fil). Skip if empty.
    lang = (language or "").strip()
    if lang:
        payload["language_code"] = lang[:8]

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{ELEVENLABS_API_BASE}/v1/text-to-speech/{vid}",
            headers=_auth_headers(settings, json_body=True),
            params={"output_format": ELEVENLABS_TTS_OUTPUT_FORMAT},
            json=payload,
        )
    if response.status_code != 200:
        body = response.text[:300]
        raise VoiceoverProviderError(
            f"ElevenLabs TTS failed with HTTP {response.status_code}: {body}"
        )
    if not response.content:
        raise VoiceoverProviderError("ElevenLabs TTS returned empty audio")
    return response.content


async def generate_elevenlabs_voiceover_mp3(
    *,
    script: str,
    voice_id: str,
    concept_id: object,
    settings: Settings,
    language: str | None = None,
) -> tuple[Path, str]:
    content = await synthesize_elevenlabs_tts_mp3_bytes(
        script=script,
        voice_id=voice_id,
        settings=settings,
        language=language,
    )
    filename = f"{safe_filename(str(concept_id))}-{uuid.uuid4().hex[:10]}.mp3"
    storage_url = store_bytes(
        content=content,
        subdir="voiceovers",
        filename=filename,
        settings=settings,
        content_type="audio/mpeg",
    )
    local_path = settings.media_path / "voiceovers" / filename
    return local_path, storage_url


__all__ = [
    "ELEVENLABS_TTS_MODEL",
    "ELEVENLABS_TTS_OUTPUT_FORMAT",
    "ElevenLabsVoiceError",
    "create_instant_voice_clone",
    "delete_elevenlabs_voice",
    "generate_elevenlabs_voiceover_mp3",
    "synthesize_elevenlabs_tts_mp3_bytes",
]
