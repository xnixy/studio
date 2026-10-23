from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings


class XaiMediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class XaiImageResult:
    url: str
    model: str | None
    cost_usd_ticks: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class XaiVideoRequestResult:
    request_id: str
    model: str | None
    cost_usd_ticks: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class XaiVideoStatusResult:
    status: str
    url: str | None
    duration: int | None
    model: str | None
    cost_usd_ticks: int | None
    error_message: str | None
    raw: dict[str, Any]


def cost_ticks_from_response(data: dict[str, Any]) -> int | None:
    usage = data.get("usage")
    if not isinstance(usage, dict):
        return None
    value = usage.get("cost_in_usd_ticks")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def first_media_url(data: dict[str, Any], media_key: str = "url") -> str | None:
    if isinstance(data.get(media_key), str):
        return str(data[media_key])

    direct = data.get("video") if media_key == "url" else None
    if isinstance(direct, dict) and isinstance(direct.get("url"), str):
        return str(direct["url"])

    rows = data.get("data")
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict) and isinstance(row.get(media_key), str):
                return str(row[media_key])
            if isinstance(row, dict) and isinstance(row.get("url"), str):
                return str(row["url"])
    return None


def video_duration_seconds_from_response(data: dict[str, Any]) -> int | None:
    video = data.get("video")
    if not isinstance(video, dict):
        return None
    duration = video.get("duration")
    if isinstance(duration, int):
        return duration
    if isinstance(duration, float):
        return int(round(duration))
    return None


def provider_error_message(data: dict[str, Any]) -> str | None:
    error = data.get("error")
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        message = error.get("message") or error.get("type") or error.get("code")
        return str(message) if message else None
    message = data.get("message")
    return str(message) if message else None


def clamp_video_duration(seconds: int, *, minimum: int = 1, maximum: int = 15) -> int:
    return max(minimum, min(maximum, int(seconds)))


def clamp_extension_duration(seconds: int) -> int:
    return clamp_video_duration(seconds, minimum=2, maximum=10)


async def generate_xai_image(
    *,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    model: str | None = None,
) -> XaiImageResult:
    if not settings.xai_api_key:
        raise XaiMediaError("xAI API key is not configured")

    model_id = (model or settings.xai_image_model).strip() or settings.xai_image_model
    payload: dict[str, Any] = {
        "model": model_id,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    data = await post_xai_json(settings.xai_image_url, payload, settings, timeout=120)
    url = first_media_url(data)
    if not url:
        raise XaiMediaError("xAI image response did not include an image URL")
    return XaiImageResult(
        url=url,
        model=str(data.get("model") or model_id),
        cost_usd_ticks=cost_ticks_from_response(data),
        raw=data,
    )


async def edit_xai_image(
    *,
    prompt: str,
    image_url: str,
    settings: Settings,
    model: str | None = None,
    aspect_ratio: str | None = None,
    resolution: str | None = None,
) -> XaiImageResult:
    """POST /v1/images/edits. Source image plus instruction. JSON body, not multipart."""
    if not settings.xai_api_key:
        raise XaiMediaError("xAI API key is not configured")
    source = (image_url or "").strip()
    if not source:
        raise XaiMediaError("Source image URL is required")
    model_id = (model or "grok-imagine-image-2.0").strip() or "grok-imagine-image-2.0"
    payload: dict[str, Any] = {
        "model": model_id,
        "prompt": prompt,
        "image": {"url": source, "type": "image_url"},
    }
    if aspect_ratio:
        payload["aspect_ratio"] = aspect_ratio
    if resolution:
        payload["resolution"] = resolution
    data = await post_xai_json(settings.xai_image_edit_url, payload, settings, timeout=120)
    url = first_media_url(data)
    if not url:
        raise XaiMediaError("xAI image edit response did not include an image URL")
    return XaiImageResult(
        url=url,
        model=str(data.get("model") or model_id),
        cost_usd_ticks=cost_ticks_from_response(data),
        raw=data,
    )


def build_xai_video_payload(
    *,
    model: str,
    prompt: str,
    duration: int,
    aspect_ratio: str,
    resolution: str,
    image_url: str | None = None,
    reference_image_urls: list[str] | None = None,
    reference_audio_voice_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build a /videos/generations body for grok-imagine-video-1.5.

    - ``image_url``: image-to-video (source becomes the first frame).
    - ``reference_image_urls``: reference-to-video. Address them in the prompt
      as ``<IMAGE_1>`` … ``<IMAGE_7>`` (1-based, matching xAI docs).
    - ``reference_audio_voice_ids``: preset / clone ids. Address as ``<AUDIO_0>``.
    Do not send ``image`` and ``reference_images`` together.
    """
    payload: dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "duration": clamp_video_duration(duration),
        "aspect_ratio": aspect_ratio,
        "resolution": resolution,
    }
    refs = [u for u in (reference_image_urls or []) if u and str(u).strip()]
    if refs:
        payload["reference_images"] = [{"url": u} for u in refs[:7]]
    elif image_url:
        payload["image"] = {"url": image_url}
    voices = [v.strip() for v in (reference_audio_voice_ids or []) if v and str(v).strip()]
    if voices:
        payload["reference_audios"] = [{"voice_id": v} for v in voices[:3]]
    return payload


async def start_xai_video(
    *,
    prompt: str,
    duration: int,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    image_url: str | None = None,
    reference_image_urls: list[str] | None = None,
    reference_audio_voice_ids: list[str] | None = None,
    model: str | None = None,
) -> XaiVideoRequestResult:
    """Start text/image/reference video generation on grok-imagine-video-1.5."""
    if not settings.xai_api_key:
        raise XaiMediaError("xAI API key is not configured")

    model_id = (model or settings.xai_video_model).strip() or settings.xai_video_model
    payload = build_xai_video_payload(
        model=model_id,
        prompt=prompt,
        duration=duration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        image_url=image_url,
        reference_image_urls=reference_image_urls,
        reference_audio_voice_ids=reference_audio_voice_ids,
    )

    data = await post_xai_json(settings.xai_video_generation_url, payload, settings, timeout=60)
    request_id = data.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise XaiMediaError("xAI video response did not include a request_id")
    return XaiVideoRequestResult(
        request_id=request_id,
        model=str(data.get("model") or model_id),
        cost_usd_ticks=cost_ticks_from_response(data),
        raw=data,
    )


async def extend_xai_video(
    *,
    prompt: str,
    video_url: str,
    duration: int,
    settings: Settings,
    model: str | None = None,
) -> XaiVideoRequestResult:
    if not settings.xai_api_key:
        raise XaiMediaError("xAI API key is not configured")

    model_id = (model or settings.xai_video_model).strip() or settings.xai_video_model
    payload: dict[str, Any] = {
        "model": model_id,
        "prompt": prompt,
        "duration": clamp_extension_duration(duration),
        "video": {"url": video_url},
    }
    data = await post_xai_json(settings.xai_video_extension_url, payload, settings, timeout=60)
    request_id = data.get("request_id")
    if not isinstance(request_id, str) or not request_id:
        raise XaiMediaError("xAI video extension response did not include a request_id")
    return XaiVideoRequestResult(
        request_id=request_id,
        model=str(data.get("model") or model_id),
        cost_usd_ticks=cost_ticks_from_response(data),
        raw=data,
    )


async def poll_xai_video(request_id: str, settings: Settings) -> XaiVideoStatusResult:
    if not settings.xai_api_key:
        raise XaiMediaError("xAI API key is not configured")

    url = f"{settings.xai_video_status_url.rstrip('/')}/{request_id}"
    data = await get_xai_json(url, settings, timeout=60)
    status = str(data.get("status") or "pending")
    return XaiVideoStatusResult(
        status=status,
        url=first_media_url(data),
        duration=video_duration_seconds_from_response(data),
        model=str(data.get("model") or settings.xai_video_model),
        cost_usd_ticks=cost_ticks_from_response(data),
        error_message=provider_error_message(data),
        raw=data,
    )


async def post_xai_json(url: str, payload: dict[str, Any], settings: Settings, *, timeout: int) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.xai_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
    return parse_xai_response(response)


async def get_xai_json(url: str, settings: Settings, *, timeout: int) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(
            url,
            headers={"Authorization": f"Bearer {settings.xai_api_key}"},
        )
    return parse_xai_response(response)


def parse_xai_response(response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        body = response.text[:300]
        lowered = body.lower()
        if response.status_code == 403 and (
            "credits" in lowered or "spending limit" in lowered or "permission-denied" in lowered
        ):
            raise XaiMediaError(
                "xAI media blocked: API credits or monthly spending limit exhausted. "
                "Scene image/video generation needs xAI credits at console.x.ai "
                f"(no local fallback). Details: {body}"
            )
        raise XaiMediaError(f"xAI media request failed with HTTP {response.status_code}: {body}")
    try:
        data = response.json()
    except ValueError:
        raise XaiMediaError("xAI media response was not JSON") from None
    if not isinstance(data, dict):
        raise XaiMediaError("xAI media response JSON must be an object")
    return data
