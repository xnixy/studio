"""Google Gemini image generation (Nano Banana family) via Interactions API."""
from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings

# Common play ratios; Gemini 3.x Flash Image accepts these.
_GEMINI_ASPECT = frozenset(
    {"1:1", "3:2", "2:3", "3:4", "4:3", "4:5", "5:4", "9:16", "16:9", "21:9"}
)


class GeminiMediaError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeminiImageResult:
    content: bytes
    mime_type: str
    model: str
    raw: dict[str, Any]


def normalize_gemini_aspect(aspect_ratio: str) -> str:
    ratio = (aspect_ratio or "1:1").strip()
    if ratio in _GEMINI_ASPECT:
        return ratio
    # Closest map for anything odd from older project configs
    if ratio in {"9:16", "3:4", "2:3"}:
        return ratio
    if ratio in {"16:9", "4:3"}:
        return ratio
    return "1:1"


def normalize_gemini_image_size(resolution: str) -> str:
    """Gemini wants uppercase K (1K / 2K / 4K). Play uses 1k-style labels."""
    raw = (resolution or "1k").strip().lower().replace(" ", "")
    if raw in {"0.5k", "512", "512px"}:
        return "0.5K"
    if raw in {"1k", "1", "1024"}:
        return "1K"
    if raw in {"2k", "2", "2048"}:
        return "2K"
    if raw in {"4k", "4", "4096"}:
        return "4K"
    return "1K"


def _extract_image_parts(data: dict[str, Any]) -> list[tuple[bytes, str]]:
    """Pull image bytes from Interactions response (convenience + steps)."""
    found: list[tuple[bytes, str]] = []

    def take(block: dict[str, Any]) -> None:
        b64 = block.get("data")
        if not isinstance(b64, str) or not b64:
            return
        mime = str(block.get("mime_type") or block.get("mimeType") or "image/jpeg")
        try:
            raw = base64.b64decode(b64, validate=False)
        except Exception as exc:  # noqa: BLE001
            raise GeminiMediaError(f"Invalid base64 image in Gemini response: {exc}") from exc
        if raw:
            found.append((raw, mime if mime.startswith("image/") else "image/jpeg"))

    # Convenience property when present
    out_img = data.get("output_image")
    if isinstance(out_img, dict):
        take(out_img)

    steps = data.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if not isinstance(step, dict):
                continue
            # Prefer final model_output over thought images
            if step.get("type") not in {"model_output", "thought", None}:
                content_lists = []
            else:
                content_lists = []
            for key in ("content", "summary", "output"):
                block = step.get(key)
                if isinstance(block, list):
                    content_lists.append(block)
                elif isinstance(block, dict):
                    content_lists.append([block])
            for items in content_lists:
                for item in items:
                    if isinstance(item, dict) and item.get("type") in {"image", "inline_data", None}:
                        if "data" in item or item.get("type") == "image":
                            take(item)

    # outputs array variants
    for key in ("outputs", "output"):
        block = data.get(key)
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict) and (item.get("type") == "image" or "data" in item):
                    take(item)
        elif isinstance(block, dict) and (block.get("type") == "image" or "data" in block):
            take(block)

    return found


async def generate_gemini_image(
    *,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    model: str | None = None,
) -> GeminiImageResult:
    if not settings.gemini_api_key:
        raise GeminiMediaError("Gemini API key is not configured")

    model_id = (model or settings.gemini_image_model).strip() or settings.gemini_image_model
    ratio = normalize_gemini_aspect(aspect_ratio)
    image_size = normalize_gemini_image_size(resolution)

    payload: dict[str, Any] = {
        "model": model_id,
        "input": [{"type": "text", "text": prompt}],
        "response_format": {
            "type": "image",
            # Interactions API currently accepts JPEG only for image mime_type.
            "mime_type": "image/jpeg",
            "aspect_ratio": ratio,
            "image_size": image_size,
        },
    }

    url = settings.gemini_interactions_url.rstrip("/")
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(url, headers=headers, json=payload)

    if response.status_code >= 400:
        body = response.text[:800]
        print(f"gemini_image_http status={response.status_code} model={model_id} body={body}", flush=True)
        raise GeminiMediaError(f"Gemini image request failed with HTTP {response.status_code}: {body}")

    try:
        data = response.json()
    except ValueError as exc:
        raise GeminiMediaError("Gemini image response was not JSON") from exc
    if not isinstance(data, dict):
        raise GeminiMediaError("Gemini image response JSON must be an object")

    images = _extract_image_parts(data)
    if not images:
        # Surface a short hint from text if present
        err = data.get("error")
        if isinstance(err, dict) and err.get("message"):
            raise GeminiMediaError(f"Gemini image failed: {err['message']}")
        raise GeminiMediaError("Gemini image response did not include image data")

    # Last image is typically the final render (thoughts may precede)
    content, mime = images[-1]
    return GeminiImageResult(
        content=content,
        mime_type=mime,
        model=str(data.get("model") or model_id),
        raw=data,
    )
