"""Kling AI video generation (official Singapore API).

Docs: https://kling.ai/dev
  Base: https://api-singapore.klingai.com
  POST /v1/videos/text2video
  POST /v1/videos/image2video
  GET  /v1/videos/text2video/{task_id}
  GET  /v1/videos/image2video/{task_id}

Auth (either):
  - Bearer API key (KLING_API_KEY)
  - JWT from AccessKey + SecretKey (KLING_ACCESS_KEY / KLING_SECRET_KEY)
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx
import jwt

from app.config import Settings

KlingMode = Literal["std", "pro"]


class KlingMediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class KlingVideoStartResult:
    task_id: str
    model: str
    endpoint: str  # text2video | image2video
    raw: dict[str, Any]


@dataclass(frozen=True)
class KlingVideoStatusResult:
    status: str  # processing | done | failed
    url: str | None
    duration: int | None
    model: str | None
    error_message: str | None
    raw: dict[str, Any]


def normalize_kling_aspect(aspect_ratio: str) -> str:
    ratio = (aspect_ratio or "9:16").strip()
    if ratio in {"16:9", "9:16", "1:1"}:
        return ratio
    if ratio in {"4:5", "3:4", "2:3"}:
        return "9:16"
    if ratio in {"4:3", "21:9", "3:2"}:
        return "16:9"
    return "9:16"


def normalize_kling_mode(resolution: str | None) -> KlingMode:
    """Map product quality chips to Kling mode (std≈720p, pro≈1080p)."""
    raw = (resolution or "720p").strip().lower()
    if raw in {"1080p", "1080", "fhd", "pro", "4k", "2160p"}:
        return "pro"
    return "std"


def clamp_kling_duration(duration: int | None, *, model: str | None = None) -> int:
    """Kling v3: 3 to 15s. Older models: 5 or 10 only."""
    s = int(duration or 5)
    model_l = (model or "").strip().lower()
    # v3 family accepts second-by-second 3–15.
    if "v3" in model_l or model_l in {"kling-v3", "kling-v3-0", "kling-v3-0-turbo"}:
        return max(3, min(s, 15))
    # Classic: only 5 or 10.
    if s <= 7:
        return 5
    return 10


def kling_configured(settings: Settings) -> bool:
    if (settings.kling_api_key or "").strip():
        return True
    ak = (settings.kling_access_key or "").strip()
    sk = (settings.kling_secret_key or "").strip()
    return bool(ak and sk)


def _base_url(settings: Settings) -> str:
    return (settings.kling_api_base_url or "https://api-singapore.klingai.com").rstrip("/")


def _jwt_token(access_key: str, secret_key: str) -> str:
    now = int(time.time())
    headers = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": access_key,
        "exp": now + 1800,
        "nbf": now - 5,
    }
    token = jwt.encode(payload, secret_key, algorithm="HS256", headers=headers)
    return token if isinstance(token, str) else token.decode("utf-8")


def _headers(settings: Settings) -> dict[str, str]:
    api_key = (settings.kling_api_key or "").strip()
    if api_key:
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    access = (settings.kling_access_key or "").strip()
    secret = (settings.kling_secret_key or "").strip()
    if not access or not secret:
        raise KlingMediaError("Kling API key is not configured")
    return {
        "Authorization": f"Bearer {_jwt_token(access, secret)}",
        "Content-Type": "application/json",
    }


def _parse_error(response: httpx.Response) -> str:
    try:
        data = response.json()
    except Exception:
        text = (response.text or "").strip()
        return text[:400] or f"HTTP {response.status_code}"
    if not isinstance(data, dict):
        return f"HTTP {response.status_code}"
    # Official shape: { code, message, request_id }
    msg = data.get("message") or data.get("msg") or data.get("error")
    code = data.get("code")
    if isinstance(msg, dict):
        msg = msg.get("message") or msg.get("msg") or str(msg)
    parts = [p for p in (str(code) if code is not None else "", str(msg or "")) if p]
    if parts:
        return ": ".join(parts)[:400]
    return f"HTTP {response.status_code}"


def _unwrap_data(data: dict[str, Any]) -> dict[str, Any]:
    """Kling wraps payloads as { code, data, message }."""
    code = data.get("code")
    if code is not None and int(code) != 0:
        msg = data.get("message") or data.get("msg") or f"Kling error code {code}"
        raise KlingMediaError(str(msg)[:400])
    inner = data.get("data")
    if isinstance(inner, dict):
        return inner
    return data


async def start_kling_video(
    *,
    prompt: str,
    duration: int,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    model: str | None = None,
    image_url: str | None = None,
    generate_audio: bool = True,
    # When True (avatar face plate): use image2video with face as first frame guide.
    identity_only: bool = False,
) -> KlingVideoStartResult:
    if not kling_configured(settings):
        raise KlingMediaError("Kling API key is not configured")

    model_id = (model or settings.kling_video_model or "kling-v3").strip() or "kling-v3"
    aspect = normalize_kling_aspect(aspect_ratio)
    mode = normalize_kling_mode(resolution)
    dur = clamp_kling_duration(duration, model=model_id)
    sound = "on" if generate_audio else "off"

    use_image = bool(image_url and str(image_url).strip())
    endpoint = "image2video" if use_image else "text2video"

    body: dict[str, Any] = {
        "model_name": model_id,
        "prompt": (prompt or "").strip(),
        "duration": str(dur),
        "mode": mode,
    }
    # Sound/audio is supported on newer models; ignore if rejected at API level.
    if "v2-6" in model_id.lower() or "v3" in model_id.lower():
        body["sound"] = sound

    if use_image:
        body["image"] = str(image_url).strip()
        # image2video derives framing from the image; aspect is still accepted on many builds.
        body["aspect_ratio"] = aspect
    else:
        body["aspect_ratio"] = aspect

    # identity_only is informational for callers; Kling image2video always uses the image as start.
    _ = identity_only

    url = f"{_base_url(settings)}/v1/videos/{endpoint}"
    async with httpx.AsyncClient(timeout=90) as client:
        response = await client.post(url, headers=_headers(settings), json=body)

    if response.status_code >= 400:
        raise KlingMediaError(_parse_error(response))

    try:
        data = response.json()
    except Exception as exc:
        raise KlingMediaError("Kling returned a non-JSON response") from exc
    if not isinstance(data, dict):
        raise KlingMediaError("Kling response was not an object")

    inner = _unwrap_data(data)
    task_id = inner.get("task_id") or inner.get("taskId") or data.get("task_id")
    if not isinstance(task_id, str) or not task_id.strip():
        # Some responses nest further
        task = inner.get("task") if isinstance(inner.get("task"), dict) else None
        if task:
            task_id = task.get("id") or task.get("task_id")
        if not isinstance(task_id, str) or not str(task_id).strip():
            raise KlingMediaError("Kling response did not include a task id")

    return KlingVideoStartResult(
        task_id=str(task_id).strip(),
        model=str(inner.get("task_info", {}).get("external_task_id") or model_id)
        if isinstance(inner.get("task_info"), dict)
        else model_id,
        endpoint=endpoint,
        raw=data,
    )


async def poll_kling_video(
    task_id: str,
    settings: Settings,
    *,
    endpoint: str | None = None,
) -> KlingVideoStatusResult:
    """Poll Kling task. Tries text2video then image2video if endpoint unknown."""
    if not task_id or not str(task_id).strip():
        raise KlingMediaError("Missing Kling task id")
    if not kling_configured(settings):
        raise KlingMediaError("Kling API key is not configured")

    tid = task_id.strip()
    candidates = []
    if endpoint in {"text2video", "image2video"}:
        candidates = [endpoint]
    else:
        candidates = ["text2video", "image2video"]

    last_error: str | None = None
    data: dict[str, Any] | None = None
    used_endpoint = candidates[0]

    async with httpx.AsyncClient(timeout=60) as client:
        for ep in candidates:
            url = f"{_base_url(settings)}/v1/videos/{ep}/{tid}"
            response = await client.get(url, headers=_headers(settings))
            if response.status_code == 404:
                last_error = f"Kling task not found on {ep}"
                continue
            if response.status_code >= 400:
                last_error = _parse_error(response)
                # 400 on wrong endpoint type — try the other
                if response.status_code in {400, 404, 422}:
                    continue
                raise KlingMediaError(last_error)
            try:
                payload = response.json()
            except Exception as exc:
                raise KlingMediaError("Kling status response was not JSON") from exc
            if not isinstance(payload, dict):
                raise KlingMediaError("Kling status response was not an object")
            data = payload
            used_endpoint = ep
            break

    if data is None:
        raise KlingMediaError(last_error or "Kling task not found")

    try:
        inner = _unwrap_data(data)
    except KlingMediaError:
        # Non-zero code mid-poll may mean failed
        code = data.get("code")
        msg = str(data.get("message") or data.get("msg") or "Kling task failed")[:400]
        if code is not None and int(code) != 0:
            return KlingVideoStatusResult(
                status="failed",
                url=None,
                duration=None,
                model=None,
                error_message=msg,
                raw=data,
            )
        raise

    raw_status = str(
        inner.get("task_status") or inner.get("status") or "processing"
    ).strip().lower()

    if raw_status in {"succeed", "succeeded", "success", "completed", "done"}:
        mapped = "done"
    elif raw_status in {"failed", "error", "canceled", "cancelled"}:
        mapped = "failed"
    else:
        mapped = "processing"

    video_url: str | None = None
    duration: int | None = None
    error_message: str | None = None

    result = inner.get("task_result") if isinstance(inner.get("task_result"), dict) else {}
    videos = result.get("videos") if isinstance(result, dict) else None
    if isinstance(videos, list) and videos:
        first = videos[0]
        if isinstance(first, dict):
            url_val = first.get("url") or first.get("video_url") or first.get("resource")
            if isinstance(url_val, str) and url_val.strip():
                video_url = url_val.strip()
            d = first.get("duration")
            if isinstance(d, (int, float)):
                duration = int(d)
            elif isinstance(d, str) and d.isdigit():
                duration = int(d)

    if mapped == "failed":
        error_message = (
            str(inner.get("task_status_msg") or inner.get("message") or "Kling generation failed")[:400]
        )

    if mapped == "done" and not video_url:
        mapped = "failed"
        error_message = "Kling finished without a video URL"

    _ = used_endpoint  # reserved for logging

    return KlingVideoStatusResult(
        status=mapped,
        url=video_url,
        duration=duration,
        model=str(inner.get("task_info", {}).get("external_task_id") or "") or None
        if isinstance(inner.get("task_info"), dict)
        else None,
        error_message=error_message,
        raw=data,
    )
