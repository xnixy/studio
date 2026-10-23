from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings
from app.media_store import public_media_url


class SyncLabsError(RuntimeError):
    pass


def sync_opens_silent_lips(settings: Settings) -> bool:
    """sync-3 can open a still mouth. lipsync-2 needs the source already talking."""
    return (settings.sync_labs_model or "sync-3").strip().lower().startswith("sync-3")


@dataclass(frozen=True)
class SyncLabsGenerationResult:
    request_id: str
    status: str
    output_url: str | None
    duration_seconds: float | None
    model: str
    error_message: str | None
    raw: dict[str, Any]


def absolute_media_url(url: str, settings: Settings) -> str:
    return public_media_url(url, settings)


async def create_sync_labs_video_dub(
    *,
    video_url: str,
    audio_url: str,
    settings: Settings,
    output_name: str,
) -> SyncLabsGenerationResult:
    """Sync-3 video + audio (dub). Kept so in-flight Grok→Sync voice_pass can finish."""
    if not settings.sync_labs_api_key:
        raise SyncLabsError("Sync Labs API key is not configured")

    payload: dict[str, Any] = {
        "model": settings.sync_labs_model,
        "input": [
            {"type": "video", "url": video_url},
            {"type": "audio", "url": audio_url},
        ],
        "outputFileName": output_name,
        # Default bounce plays a short Grok take backwards over longer TTS.
        # That smears faces and makes the line run last-to-first. cut_off never
        # reverses. Auto-detect keeps a silent listener's mouth still.
        "options": {
            "sync_mode": "cut_off",
            "active_speaker_detection": {"auto_detect": True},
        },
    }
    data = await sync_labs_json(
        "POST",
        f"{settings.sync_labs_base_url.rstrip('/')}/v2/generate",
        settings,
        json=payload,
        timeout=60,
    )
    return parse_generation(data, fallback_model=settings.sync_labs_model)


async def poll_sync_labs_generation(request_id: str, settings: Settings) -> SyncLabsGenerationResult:
    if not settings.sync_labs_api_key:
        raise SyncLabsError("Sync Labs API key is not configured")

    url = f"{settings.sync_labs_base_url.rstrip('/')}/v2/generate/{request_id}"
    data = await sync_labs_json("GET", url, settings, timeout=60)
    return parse_generation(data, fallback_model=settings.sync_labs_model)


async def sync_labs_json(method: str, url: str, settings: Settings, *, timeout: int, json: dict[str, Any] | None = None) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(
            method,
            url,
            headers={
                "x-api-key": settings.sync_labs_api_key or "",
                "Content-Type": "application/json",
            },
            json=json,
        )
    if response.status_code >= 400:
        raise SyncLabsError(f"Sync Labs request failed with HTTP {response.status_code}: {response.text[:300]}")
    try:
        data = response.json()
    except ValueError:
        raise SyncLabsError("Sync Labs response was not JSON") from None
    if not isinstance(data, dict):
        raise SyncLabsError("Sync Labs response JSON must be an object")
    return data


def parse_generation(data: dict[str, Any], *, fallback_model: str) -> SyncLabsGenerationResult:
    request_id = data.get("id")
    if not isinstance(request_id, str) or not request_id:
        raise SyncLabsError("Sync Labs response did not include a generation id")
    status = str(data.get("status") or "PENDING")
    duration = data.get("outputDuration")
    error = data.get("error")
    return SyncLabsGenerationResult(
        request_id=request_id,
        status=status,
        output_url=str(data["outputUrl"]) if isinstance(data.get("outputUrl"), str) and data.get("outputUrl") else None,
        duration_seconds=float(duration) if isinstance(duration, int | float) else None,
        model=str(data.get("model") or fallback_model),
        error_message=str(error) if error else None,
        raw=data,
    )
