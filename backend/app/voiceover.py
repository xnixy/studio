from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path

import httpx

from app.config import Settings
from app.media_store import store_bytes
from app.stock_voices import (  # noqa: F401
    DEFAULT_STOCK_VOICE_ID,
    FEATURED_VOICE_IDS,
    LEGACY_XAI_VOICE_IDS,
    STOCK_VOICES,
    builtin_voice_rows,
    sort_builtin_voices,
)

log = logging.getLogger(__name__)

# Short line for in-app voice previews (keep under ~15 words to stay cheap).
VOICE_PREVIEW_SCRIPT = "Hi, this is a quick preview of this voice for your clip."

# Legacy UI values → xAI picture stand-in ids (overridable via settings).
LEGACY_VOICE_ALIASES = {"female", "male"}

# Retired xAI picker names still resolve for leftover TTS / Grok stand-ins.
_XAI_STANDIN_IDS = LEGACY_XAI_VOICE_IDS - {"male", "female"}


class VoiceoverProviderError(RuntimeError):
    pass


def voice_id_for(voice: str, settings: Settings) -> str:
    """Map a value to an xAI voice_id for Grok stand-in or leftover xAI TTS.

    Stock picker ids (jessica, …) are not xAI ids. Callers that need ElevenLabs
    should use stock_voices.elevenlabs_voice_id_for.
    """
    key = (voice or "").strip().lower()
    if key in _XAI_STANDIN_IDS:
        return key
    if key == "male":
        return (settings.xai_tts_male_voice_id or "rex").strip().lower()
    if key == "female":
        return (settings.xai_tts_female_voice_id or "ara").strip().lower()
    if key and re.fullmatch(r"[a-z0-9_-]{2,64}", key):
        return key
    return (settings.xai_tts_female_voice_id or "ara").strip().lower()


def clamp_speech_speed(speed: float | None, fallback: float = 1.0) -> float:
    value = fallback if speed is None else float(speed)
    return max(0.7, min(1.5, round(value, 3)))


def speech_speed_for(speed_override: float | None = None) -> float:
    """Natural pace unless a caller asks for something else.

    Delivery presets used to live here from the ad-script product ("energetic",
    "ugc-style"). Play has no concept of an ad read, the built-in voices already
    carry their own character, and forcing a preset made every lip-sync 5% fast.
    """
    if speed_override is None:
        return 1.0
    return clamp_speech_speed(speed_override)


def expand_spoken_domains(text: str) -> str:
    """Make domains speakable so TTS does not skip or mumble them.

    xAI TTS often soft-drops bare hostnames like example.com under normalization.
    Expanding to “example dot com” forces a clear read.
    """

    def _dom(m: re.Match[str]) -> str:
        start = m.start()
        if start > 0 and text[start - 1] == "@":
            return m.group(0)
        return f"{m.group(1)} dot {m.group(2)}"

    text = re.sub(
        r"\b([a-zA-Z0-9-]{2,40})\.(com|io|ai|app|co|dev|net|org)\b",
        _dom,
        text,
    )
    return text


def voiceover_text(script: str) -> str:
    """Prepare a script for TTS.

    xAI supports inline tags ([pause], [laugh]) and wrapping tags
    (<whisper>…</whisper>, <soft>…</soft>, <slow>…</slow>). We never inject them:
    whatever the user wrote is what gets read.
    """
    return expand_spoken_domains(script.strip())


def estimate_voiceover_seconds(script: str) -> int:
    """Rough TTS duration from word count (min 5s)."""
    words = [word for word in script.split() if word.strip()]
    return max(5, round(len(words) / 2.55))


def safe_filename(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return value[:64] or "voiceover"


async def synthesize_xai_tts_mp3_bytes(
    *,
    script: str,
    voice: str,
    settings: Settings,
    language: str | None = None,
    speed: float | None = None,
    text_normalization: bool = True,
    timeout: float = 90,
) -> bytes:
    """Call xAI TTS and return raw MP3 bytes (no storage)."""
    if not settings.xai_api_key:
        raise VoiceoverProviderError("xAI API key is not configured")

    text = voiceover_text(str(script)).strip()
    if not text:
        raise VoiceoverProviderError("Script is empty")

    lang = (language or settings.xai_tts_language or "en").strip() or "en"
    voice_id = voice_id_for(str(voice), settings)
    payload = {
        "text": text,
        "voice_id": voice_id,
        "language": lang,
        "speed": speech_speed_for(speed),
        "text_normalization": bool(text_normalization),
        "output_format": {"codec": "mp3", "sample_rate": 44100, "bit_rate": 192000},
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            settings.xai_tts_url,
            headers={
                "Authorization": f"Bearer {settings.xai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code != 200:
        body = response.text[:300]
        if response.status_code == 403 and (
            "credits" in body.lower()
            or "spending limit" in body.lower()
            or "permission-denied" in body.lower()
        ):
            raise VoiceoverProviderError(
                "xAI TTS blocked: API credits or monthly spending limit exhausted. "
                "Add credits at console.x.ai. "
                f"Details: {body}"
            )
        if response.status_code == 404:
            raise VoiceoverProviderError(f"Unknown voice id. Try another voice. Details: {body}")
        raise VoiceoverProviderError(f"xAI TTS failed with HTTP {response.status_code}: {body}")

    if not response.content:
        raise VoiceoverProviderError("xAI TTS returned empty audio")
    return response.content


async def generate_xai_voiceover_mp3(
    *,
    script: str,
    voice: str,
    concept_id: object,
    settings: Settings,
    language: str | None = None,
    speed: float | None = None,
    text_normalization: bool = True,
) -> tuple[Path, str]:
    content = await synthesize_xai_tts_mp3_bytes(
        script=script,
        voice=voice,
        settings=settings,
        language=language,
        speed=speed,
        text_normalization=text_normalization,
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
