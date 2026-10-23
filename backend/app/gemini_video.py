"""Google Veo video generation via Gemini API predictLongRunning."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

log = logging.getLogger(__name__)


class GeminiVideoError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiVideoStartResult:
    operation_name: str
    model: str
    raw: dict[str, Any]


@dataclass(frozen=True)
class GeminiVideoStatusResult:
    status: str  # processing | done | failed
    url: str | None
    model: str | None
    error_message: str | None
    raw: dict[str, Any]


def _gemini_headers(settings: Settings) -> dict[str, str]:
    return {
        "x-goog-api-key": settings.gemini_api_key or "",
        "Content-Type": "application/json",
    }


def _base_v1beta(settings: Settings) -> str:
    # interactions URL is .../v1beta/interactions → strip to .../v1beta
    base = settings.gemini_interactions_url.rstrip("/")
    if base.endswith("/interactions"):
        base = base[: -len("/interactions")]
    if not base.endswith("/v1beta"):
        base = "https://generativelanguage.googleapis.com/v1beta"
    return base


def normalize_veo_aspect(aspect_ratio: str) -> str:
    """Veo on Gemini API only accepts 9:16 or 16:9 (no true 1:1)."""
    ratio = (aspect_ratio or "9:16").strip()
    if ratio in {"9:16", "16:9"}:
        return ratio
    # Square / portrait social → vertical; landscape-ish → 16:9
    if ratio in {"1:1", "4:5", "3:4", "2:3"}:
        print(f"veo_aspect map {ratio}→9:16 (Veo has no square)", flush=True)
        return "9:16"
    if ratio in {"4:3", "21:9", "3:2"}:
        print(f"veo_aspect map {ratio}→16:9", flush=True)
        return "16:9"
    return "9:16"


def normalize_veo_resolution(resolution: str) -> str:
    raw = (resolution or "720p").strip().lower()
    if raw in {"1080p", "1080", "fhd"}:
        return "1080p"
    if raw in {"4k", "2160p"}:
        # Keep cost/latency reasonable for play; 4k also forces 8s-only on many Veo SKUs
        return "720p"
    return "720p"


# Veo 3.1 on the Gemini API accepts referenceImages only at 8 seconds. A 4s or 6s
# request with referenceImages attached comes back as
#   400 INVALID_ARGUMENT "Your use case is currently not supported."
# which reads like a model outage but is really this constraint. Talking clips always
# attach a face plate, so every avatar clip must be 8s.
# https://ai.google.dev/gemini-api/docs/veo
VEO_REFERENCE_IMAGE_DURATION = 8


def normalize_veo_duration(
    seconds: int | None, *, resolution: str = "720p", has_reference_images: bool = False
) -> int:
    """Veo 3.1 on Gemini API: 4, 6, or 8 seconds. 1080p+ and referenceImages are 8s-only."""
    if has_reference_images:
        return VEO_REFERENCE_IMAGE_DURATION
    res = normalize_veo_resolution(resolution)
    if res in {"1080p", "4k"}:
        return 8
    s = int(seconds or 8)
    if s <= 4:
        return 4
    if s <= 6:
        return 6
    return 8


def _veo_image_from_data_url(data_url: str) -> dict[str, Any] | None:
    """Veo predictLongRunning image part (not Gemini generateContent inlineData)."""
    if not data_url.startswith("data:"):
        return None
    try:
        header, b64 = data_url.split(",", 1)
        mime = "image/jpeg"
        if ";" in header:
            mime = header[5:].split(";")[0] or mime
        # Veo rejects `inlineData` with 400; use bytesBase64Encoded.
        return {"bytesBase64Encoded": b64, "mimeType": mime or "image/jpeg"}
    except ValueError:
        return None


async def _fetch_image_as_veo_part(url: str, settings: Settings) -> dict[str, Any] | None:
    """Load an image URL/data-URL into a Veo image object.

    Format required by models/{veo}:predictLongRunning:
      {"bytesBase64Encoded": "...", "mimeType": "image/jpeg"}
    Using Gemini generateContent's inlineData shape causes:
      "`inlineData` isn't supported by this model"

    Prefer local disk / R2 bytes over HTTP self-fetch so private /api/media faces
    work in production (avoids CF hairpin + auth failures).
    """
    if not url:
        return None
    if url.startswith("data:"):
        return _veo_image_from_data_url(url)

    from app.media_signing import strip_media_query
    from app.media_store import (
        MediaStoreError,
        content_type_for_key,
        ensure_local_media,
        get_r2_bytes,
        key_from_storage_url,
        local_path_for_key,
        r2_enabled,
    )

    content: bytes | None = None
    mime = "image/jpeg"
    clean = strip_media_query(url)
    preview = (url[:120] + "…") if len(url) > 120 else url

    try:
        key = key_from_storage_url(clean, settings)
        if key:
            path = local_path_for_key(key, settings)
            if path.exists() and path.stat().st_size > 0:
                content = path.read_bytes()
                mime = content_type_for_key(key) or mime
            elif r2_enabled(settings):
                content = get_r2_bytes(key, settings)
                mime = content_type_for_key(key) or mime
    except Exception as exc:  # noqa: BLE001 — fall through to other loaders
        print(f"veo_image local/r2 failed url={preview}: {exc}", flush=True)

    if content is None:
        try:
            path = ensure_local_media(clean if (clean.startswith("/") or clean.startswith("http")) else url, settings)
            if path.exists() and path.stat().st_size > 0:
                content = path.read_bytes()
                mime = content_type_for_key(path.name) or mime
        except MediaStoreError as exc:
            print(f"veo_image ensure_local failed url={preview}: {exc}", flush=True)

    if content is None and (url.startswith("http://") or url.startswith("https://")):
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                response = await client.get(url)
            if response.status_code < 400 and response.content:
                content = response.content
                ctype = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
                if ctype.startswith("image/"):
                    mime = ctype
            else:
                print(
                    f"veo_image http status={getattr(response, 'status_code', '?')} url={preview}",
                    flush=True,
                )
        except Exception as exc:  # noqa: BLE001
            print(f"veo_image http error url={preview}: {exc}", flush=True)

    if not content:
        print(f"veo_image empty url={preview}", flush=True)
        return None
    if len(content) > 12 * 1024 * 1024:
        print(f"veo_image too large bytes={len(content)} url={preview}", flush=True)
        return None
    if not mime.startswith("image/"):
        mime = "image/jpeg"
    return {
        "bytesBase64Encoded": base64.b64encode(content).decode("ascii"),
        "mimeType": mime,
    }


async def _load_veo_parts(urls: list[str], settings: Settings) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for u in urls:
        if not u:
            continue
        part = await _fetch_image_as_veo_part(u, settings)
        if part:
            parts.append(part)
        else:
            preview = (u[:100] + "…") if len(u) > 100 else u
            print(f"veo_image skip (unreadable) url={preview}", flush=True)
    return parts


async def start_gemini_video(
    *,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    model: str | None = None,
    image_url: str | None = None,
    reference_image_urls: list[str] | None = None,
    duration_seconds: int | None = None,
    # When True (avatar face plates): images are identity refs only, never first-frame.
    # First-framing a studio headshot makes Veo open on the plate, ignore aspect, and glitch audio.
    identity_only: bool = False,
    person_generation: str = "allow_adult",
) -> GeminiVideoStartResult:
    if not settings.gemini_api_key:
        raise GeminiVideoError("Gemini API key is not configured")

    model_id = (model or settings.gemini_video_model).strip() or settings.gemini_video_model
    res = normalize_veo_resolution(resolution)
    aspect = normalize_veo_aspect(aspect_ratio)
    duration = normalize_veo_duration(duration_seconds, resolution=res)

    instance: dict[str, Any] = {"prompt": prompt}

    first_urls = [image_url] if image_url else []
    ref_urls = [u for u in (reference_image_urls or []) if u]

    if identity_only:
        # Avatar face stills: ingredients-to-video / referenceImages path only.
        identity_urls = [*first_urls, *ref_urls][:3]
        parts = await _load_veo_parts(identity_urls, settings)
        if identity_urls and not parts:
            preview = (identity_urls[0][:100] + "…") if identity_urls[0] else ""
            print(
                f"veo identity load failed count={len(identity_urls)} first={preview}",
                flush=True,
            )
            raise GeminiVideoError(
                "Could not load the face or reference image for Veo. "
                "Re-save the face photo and try again, or pick Seedance / Grok."
            )
        if parts:
            instance["referenceImages"] = [
                {"image": part, "referenceType": "asset"} for part in parts
            ]
            duration = VEO_REFERENCE_IMAGE_DURATION
    else:
        # Scene image-to-video: first image is the first frame; extras are optional refs.
        frame_url = first_urls[0] if first_urls else (ref_urls[0] if ref_urls else None)
        extra_urls = (
            ref_urls
            if first_urls
            else ref_urls[1:3]
        )
        if frame_url:
            parts = await _load_veo_parts([frame_url], settings)
            if parts:
                instance["image"] = parts[0]
            else:
                raise GeminiVideoError("Could not load the first-frame image for Veo")
        if extra_urls:
            extra = await _load_veo_parts(list(extra_urls)[:3], settings)
            if extra:
                instance["referenceImages"] = [
                    {"image": part, "referenceType": "asset"} for part in extra
                ]
                duration = VEO_REFERENCE_IMAGE_DURATION

    parameters: dict[str, Any] = {
        "aspectRatio": aspect,
        "resolution": res,
        "durationSeconds": duration,
        "sampleCount": 1,
    }
    # Required for clips that include people on many Veo SKUs.
    if person_generation:
        parameters["personGeneration"] = person_generation

    payload: dict[str, Any] = {
        "instances": [instance],
        "parameters": parameters,
    }

    url = f"{_base_v1beta(settings)}/models/{model_id}:predictLongRunning"
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(url, headers=_gemini_headers(settings), json=payload)

    # Never drop the face for avatar: text-only would invent a different person.
    if response.status_code >= 400 and identity_only and "reference" in response.text.lower():
        log.warning(
            "Veo rejected referenceImages for avatar (status=%s body=%s)",
            response.status_code,
            response.text[:300],
        )
        body_l = response.text.lower()
        if "isn't supported" in body_l or "is not supported" in body_l or "not supported by this model" in body_l:
            raise GeminiVideoError(
                f"{model_id} cannot use a face reference. "
                "Clear the avatar or pick full Veo 3.1 / Seedance / Grok."
            )
        raise GeminiVideoError(
            "Veo rejected the face reference. Re-save the face as a clear front photo, "
            "or try Grok / Seedance for this clip."
        )

    if response.status_code >= 400:
        detail = response.text[:800]
        print(
            f"gemini_video_http status={response.status_code} model={model_id} body={detail}",
            flush=True,
        )
        if "inlineData" in detail:
            detail = (
                "Veo rejected the image payload format. "
                "Try again, or use Seedance / Grok for talking clips with a face."
            )
        raise GeminiVideoError(
            f"Gemini video start failed with HTTP {response.status_code}: {detail}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise GeminiVideoError("Gemini video start response was not JSON") from exc
    if not isinstance(data, dict):
        raise GeminiVideoError("Gemini video start response must be an object")

    name = data.get("name")
    if not isinstance(name, str) or not name:
        raise GeminiVideoError("Gemini video response did not include an operation name")
    return GeminiVideoStartResult(operation_name=name, model=model_id, raw=data)


def _extract_video_uri(data: dict[str, Any]) -> str | None:
    # response.generateVideoResponse.generatedSamples[0].video.uri
    resp = data.get("response")
    if not isinstance(resp, dict):
        return None
    gvr = resp.get("generateVideoResponse") or resp.get("generate_video_response")
    if not isinstance(gvr, dict):
        # alternate shapes
        samples = resp.get("generatedVideos") or resp.get("generated_videos")
        if isinstance(samples, list) and samples:
            first = samples[0]
            if isinstance(first, dict):
                video = first.get("video") or first
                if isinstance(video, dict) and isinstance(video.get("uri"), str):
                    return video["uri"]
        return None
    samples = gvr.get("generatedSamples") or gvr.get("generated_samples") or []
    if not isinstance(samples, list) or not samples:
        return None
    first = samples[0]
    if not isinstance(first, dict):
        return None
    video = first.get("video")
    if isinstance(video, dict) and isinstance(video.get("uri"), str):
        return video["uri"]
    return None


async def poll_gemini_video(operation_name: str, settings: Settings) -> GeminiVideoStatusResult:
    if not settings.gemini_api_key:
        raise GeminiVideoError("Gemini API key is not configured")

    name = operation_name.strip().lstrip("/")
    url = f"{_base_v1beta(settings)}/{name}" if not name.startswith("http") else name
    # If name is already full operations path under v1beta
    if not name.startswith("http") and not name.startswith("operations") and "/operations/" not in name:
        # name is usually "operations/..."
        url = f"{_base_v1beta(settings)}/{name}"

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(url, headers={"x-goog-api-key": settings.gemini_api_key or ""})

    if response.status_code >= 400:
        raise GeminiVideoError(
            f"Gemini video poll failed with HTTP {response.status_code}: {response.text[:300]}"
        )
    try:
        data = response.json()
    except ValueError as exc:
        raise GeminiVideoError("Gemini video poll response was not JSON") from exc
    if not isinstance(data, dict):
        raise GeminiVideoError("Gemini video poll response must be an object")

    if data.get("error"):
        err = data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        return GeminiVideoStatusResult(
            status="failed",
            url=None,
            model=None,
            error_message=str(msg) if msg else "Gemini video failed",
            raw=data,
        )

    if not data.get("done"):
        return GeminiVideoStatusResult(
            status="processing",
            url=None,
            model=None,
            error_message=None,
            raw=data,
        )

    uri = _extract_video_uri(data)
    if not uri:
        return GeminiVideoStatusResult(
            status="failed",
            url=None,
            model=None,
            error_message="Gemini video completed without a download URI",
            raw=data,
        )
    return GeminiVideoStatusResult(
        status="done",
        url=uri,
        model=None,
        error_message=None,
        raw=data,
    )


async def download_gemini_video_url(url: str, settings: Settings) -> bytes:
    """Download a Veo result URI (requires API key)."""
    if not settings.gemini_api_key:
        raise GeminiVideoError("Gemini API key is not configured")
    async with httpx.AsyncClient(timeout=180, follow_redirects=True) as client:
        response = await client.get(
            url,
            headers={"x-goog-api-key": settings.gemini_api_key},
        )
    if response.status_code >= 400:
        raise GeminiVideoError(
            f"Gemini video download failed with HTTP {response.status_code}: {response.text[:200]}"
        )
    content = response.content
    if not content:
        raise GeminiVideoError("Gemini video download was empty")
    return content
