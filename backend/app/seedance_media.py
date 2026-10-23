"""Seedance video generation via the seevio.ai async API.

Was seedance2.ai until the July 2026 rebrand; same API, same paths, new host.

API: https://seevio.ai/api-docs
  POST /v1/videos/generations
  GET  /v1/tasks/{taskId}

Models: seedance-2-5 (recommended, 4-30s, 480p/720p), seedance-2-0 / fast / mini (4-15s).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.config import Settings

SeedanceGenerationType = Literal["text-to-video", "image-to-video", "reference-to-video"]


class SeedanceMediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class SeedanceVideoStartResult:
    task_id: str
    model: str
    credits: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class SeedanceVideoStatusResult:
    status: str  # processing | done | failed
    url: str | None
    last_frame_url: str | None
    duration: int | None
    model: str | None
    error_message: str | None
    raw: dict[str, Any]


def normalize_seedance_aspect(aspect_ratio: str) -> str:
    ratio = (aspect_ratio or "adaptive").strip()
    allowed = {"16:9", "9:16", "4:3", "3:4", "21:9", "1:1", "adaptive"}
    if ratio in allowed:
        return ratio
    if ratio in {"4:5", "2:3"}:
        return "9:16"
    return "adaptive"


def is_seedance_25(model: str | None) -> bool:
    """True for Seedance 2.5 catalog or provider ids (Scene and Talking)."""
    m = (model or "").strip().lower().replace("_", "-")
    if m in {"seedance-avatar", "seedance-2-5", "seedance-photo"}:
        return True
    return "2-5" in m or "2.5" in m


def normalize_seedance_resolution(resolution: str, *, model: str | None = None) -> str:
    raw = (resolution or "720p").strip().lower().replace(" ", "")
    if raw in {"480", "480p"}:
        res = "480p"
    elif raw in {"720", "720p", "hd"}:
        res = "720p"
    elif raw in {"1080", "1080p", "fhd"}:
        res = "1080p"
    elif raw in {"4k", "2160", "2160p", "uhd"}:
        res = "4k"
    else:
        res = "720p"
    # Seedance 2.5 only accepts 480p or 720p.
    if is_seedance_25(model) and res in {"1080p", "4k"}:
        return "720p"
    return res


def clamp_seedance_duration(duration: int, *, model: str | None = None) -> int:
    cap = 30 if is_seedance_25(model) else 15
    return max(4, min(int(duration or 5), cap))


def _headers(settings: Settings) -> dict[str, str]:
    key = (settings.seedance_api_key or "").strip()
    if not key:
        raise SeedanceMediaError("Seedance API key is not configured")
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _base_url(settings: Settings) -> str:
    return (settings.seedance_api_base_url or "https://api.seevio.ai").rstrip("/")


def _parse_error(response: httpx.Response) -> str:
    try:
        data = response.json()
    except Exception:
        text = (response.text or "").strip()
        return text[:400] or f"HTTP {response.status_code}"
    err = data.get("error") if isinstance(data, dict) else None
    if isinstance(err, dict):
        code = err.get("code") or ""
        message = err.get("message") or ""
        parts = [p for p in (str(code), str(message)) if p]
        if parts:
            return ": ".join(parts)[:400]
    if isinstance(data, dict) and data.get("message"):
        return str(data["message"])[:400]
    return f"HTTP {response.status_code}"


async def start_seedance_video(
    *,
    prompt: str,
    duration: int,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    model: str | None = None,
    generation_type: SeedanceGenerationType = "text-to-video",
    image_urls: list[str] | None = None,
    video_urls: list[str] | None = None,
    audio_urls: list[str] | None = None,
    generate_audio: bool = True,
    watermark: bool = False,
    return_last_frame: bool = False,
    seed: int = -1,
    callback_url: str | None = None,
    # When True (avatar face plates): never use image-to-video first-frame mode.
    identity_only: bool = False,
) -> SeedanceVideoStartResult:
    """Submit an async Seedance video task. Returns task id for polling."""
    model_id = (model or settings.seedance_video_model).strip() or settings.seedance_video_model
    images = [u.strip() for u in (image_urls or []) if u and str(u).strip()]
    videos = [u.strip() for u in (video_urls or []) if u and str(u).strip()]
    audios = [u.strip() for u in (audio_urls or []) if u and str(u).strip()]

    gen_type: SeedanceGenerationType = generation_type

    # Face plates / identity: always reference-to-video.
    # image-to-video treats image_urls[0] as the literal first frame (studio headshot open).
    if identity_only and images:
        gen_type = "reference-to-video"

    # Auto-upgrade text-to-video when media is present.
    # Prefer reference-to-video for a single image so face stills are not first-framed by accident.
    if gen_type == "text-to-video" and (images or videos or audios):
        if videos or audios or images:
            gen_type = "reference-to-video"
        # (explicit image-to-video is only when the caller passes generation_type=image-to-video)

    # Multi-material or identity cannot be pure first-frame i2v.
    if gen_type == "image-to-video" and (identity_only or videos or audios or len(images) > 2):
        gen_type = "reference-to-video"

    if gen_type == "image-to-video" and not images:
        raise SeedanceMediaError("image-to-video requires at least one image URL")
    if gen_type == "reference-to-video" and not images and not videos:
        if not (is_seedance_25(model_id) and audios):
            raise SeedanceMediaError(
                "reference-to-video needs at least one image, video, or (2.5) audio reference"
            )
    if audios and not images and not videos and not is_seedance_25(model_id):
        raise SeedanceMediaError("Audio needs at least one image or video reference")

    # Explicit aspect when we know platform (avoid adaptive ignoring 9:16 on mobile).
    aspect = normalize_seedance_aspect(aspect_ratio)
    # Seedance 2.5 image-to-video only accepts adaptive.
    if is_seedance_25(model_id) and gen_type == "image-to-video":
        aspect = "adaptive"
    res = normalize_seedance_resolution(resolution, model=model_id)
    dur = clamp_seedance_duration(duration, model=model_id)

    input_body: dict[str, Any] = {
        "prompt": prompt.strip(),
        "generation_type": gen_type,
        "duration": dur,
        "aspect_ratio": aspect,
        "resolution": res,
        "generate_audio": bool(generate_audio),
        "watermark": bool(watermark),
        "web_search": False,
        "return_last_frame": bool(return_last_frame),
    }
    # Seedance 2.5 rejects seed; 2.0 variants honor it.
    if not is_seedance_25(model_id):
        input_body["seed"] = int(seed) if seed is not None else -1
    if images:
        # image-to-video: 1 first frame or 2 first+last; reference: 30 on 2.5, 9 on 2.0
        if gen_type == "image-to-video":
            img_limit = 2
        else:
            img_limit = 30 if is_seedance_25(model_id) else 9
        input_body["image_urls"] = images[:img_limit]
    if videos and gen_type == "reference-to-video":
        vid_limit = 10 if is_seedance_25(model_id) else 3
        input_body["video_urls"] = videos[:vid_limit]
    if audios and gen_type == "reference-to-video":
        aud_limit = 10 if is_seedance_25(model_id) else 3
        input_body["audio_urls"] = audios[:aud_limit]

    payload: dict[str, Any] = {
        "model": model_id,
        "input": input_body,
    }
    if callback_url:
        payload["callback_url"] = callback_url

    url = f"{_base_url(settings)}/v1/videos/generations"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(url, headers=_headers(settings), json=payload)

    if response.status_code >= 400:
        raise SeedanceMediaError(_parse_error(response))

    try:
        data = response.json()
    except Exception as exc:
        raise SeedanceMediaError("Seedance returned a non-JSON response") from exc
    if not isinstance(data, dict):
        raise SeedanceMediaError("Seedance response was not an object")

    task_id = data.get("taskId") or data.get("task_id") or data.get("id")
    if not isinstance(task_id, str) or not task_id.strip():
        raise SeedanceMediaError("Seedance response did not include a task id")

    credits = data.get("credits")
    credits_i = int(credits) if isinstance(credits, (int, float)) else None

    return SeedanceVideoStartResult(
        task_id=task_id.strip(),
        model=str(data.get("model") or model_id),
        credits=credits_i,
        raw=data,
    )


async def poll_seedance_video(task_id: str, settings: Settings) -> SeedanceVideoStatusResult:
    """Poll task status. Maps Seedance statuses to processing | done | failed."""
    if not task_id or not str(task_id).strip():
        raise SeedanceMediaError("Missing Seedance task id")

    url = f"{_base_url(settings)}/v1/tasks/{task_id.strip()}"
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers=_headers(settings))

    if response.status_code >= 400:
        raise SeedanceMediaError(_parse_error(response))

    try:
        data = response.json()
    except Exception as exc:
        raise SeedanceMediaError("Seedance status response was not JSON") from exc
    if not isinstance(data, dict):
        raise SeedanceMediaError("Seedance status response was not an object")

    raw_status = str(data.get("status") or "queued").strip().lower()
    model = str(data.get("model") or settings.seedance_video_model)

    if raw_status in {"completed", "succeeded", "success", "done"}:
        result_data = data.get("data") if isinstance(data.get("data"), dict) else {}
        results = result_data.get("results") if isinstance(result_data, dict) else None
        video_url: str | None = None
        if isinstance(results, list) and results:
            first = results[0]
            if isinstance(first, str) and first.strip():
                video_url = first.strip()
            elif isinstance(first, dict):
                for key in ("url", "video_url", "result"):
                    val = first.get(key)
                    if isinstance(val, str) and val.strip():
                        video_url = val.strip()
                        break
        last_frame = None
        if isinstance(result_data, dict):
            lf = result_data.get("last_frame_url")
            if isinstance(lf, str) and lf.strip():
                last_frame = lf.strip()
        duration = None
        if isinstance(result_data, dict) and isinstance(result_data.get("duration"), (int, float)):
            duration = int(result_data["duration"])
        if not video_url:
            return SeedanceVideoStatusResult(
                status="failed",
                url=None,
                last_frame_url=last_frame,
                duration=duration,
                model=model,
                error_message="Seedance completed without a video URL",
                raw=data,
            )
        return SeedanceVideoStatusResult(
            status="done",
            url=video_url,
            last_frame_url=last_frame,
            duration=duration,
            model=model,
            error_message=None,
            raw=data,
        )

    if raw_status in {"failed", "error", "cancelled", "canceled", "timeout", "timed_out"}:
        failed_reason = data.get("failed_reason")
        if not failed_reason and isinstance(data.get("data"), dict):
            failed_reason = data["data"].get("failed_reason")
        return SeedanceVideoStatusResult(
            status="failed",
            url=None,
            last_frame_url=None,
            duration=None,
            model=model,
            error_message=str(failed_reason or f"Seedance task {raw_status}")[:400],
            raw=data,
        )

    # queued | generating | processing | pending | ...
    return SeedanceVideoStatusResult(
        status="processing",
        url=None,
        last_frame_url=None,
        duration=None,
        model=model,
        error_message=None,
        raw=data,
    )
