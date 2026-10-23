"""Shared image generation across xAI (Grok) and Google Gemini (Nano Banana)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import Settings
from app.gemini_media import GeminiMediaError, generate_gemini_image
from app.media_store import download_media_url, store_bytes
from app.play_models import PLAY_MODELS, PlayModel, get_play_model
from app.xai_media import XaiMediaError, generate_xai_image


class ImageProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class GeneratedImage:
    provider: str
    model: str
    model_id: str | None
    url: str | None
    content: bytes | None
    mime_type: str | None
    cost_usd_ticks: int | None
    raw: dict[str, Any]


def resolve_image_model(model: str | None, settings: Settings) -> PlayModel:
    """Resolve a play model id or provider model string to an image catalog entry."""
    if model:
        key = model.strip()
        for m in PLAY_MODELS:
            if m.modality != "image" or not m.enabled:
                continue
            if m.id == key or m.provider_model == key:
                return m
        # Unknown id: treat as raw provider model
        if key.startswith("gemini") or "nano-banana" in key.lower():
            return PlayModel(
                id=key,
                label=key,
                modality="image",
                provider="gemini",
                provider_model=key if key.startswith("gemini") else settings.gemini_image_model,
                blurb="",
                credit_meter="image_generation",
            )
        return PlayModel(
            id=key,
            label=key,
            modality="image",
            provider="xai",
            provider_model=key if key.startswith("grok") else (key or settings.xai_image_model),
            blurb="",
            credit_meter="image_generation",
        )
    return get_play_model(None, "image")


def ensure_image_provider_configured(play_model: PlayModel, settings: Settings) -> None:
    provider = (play_model.provider or "xai").lower()
    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ImageProviderError("Gemini API key is not configured")
    elif not settings.xai_api_key:
        raise ImageProviderError("xAI API key is not configured")


async def generate_image(
    *,
    prompt: str,
    aspect_ratio: str,
    resolution: str,
    settings: Settings,
    model: str | None = None,
) -> GeneratedImage:
    play_model = resolve_image_model(model, settings)
    ensure_image_provider_configured(play_model, settings)
    provider = (play_model.provider or "xai").lower()

    try:
        if provider == "gemini":
            result = await generate_gemini_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                settings=settings,
                model=play_model.provider_model,
            )
            return GeneratedImage(
                provider="gemini",
                model=result.model,
                model_id=play_model.id,
                url=None,
                content=result.content,
                mime_type=result.mime_type,
                cost_usd_ticks=None,
                raw=result.raw,
            )

        result = await generate_xai_image(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            settings=settings,
            model=play_model.provider_model,
        )
        return GeneratedImage(
            provider="xai",
            model=result.model or play_model.provider_model,
            model_id=play_model.id,
            url=result.url,
            content=None,
            mime_type=None,
            cost_usd_ticks=result.cost_usd_ticks,
            raw=result.raw,
        )
    except (XaiMediaError, GeminiMediaError) as exc:
        raise ImageProviderError(str(exc)) from exc


async def persist_generated_image(
    *,
    result: GeneratedImage,
    settings: Settings,
    subdir: str,
    stem: object,
) -> str:
    """Store generated image; returns storage URL."""
    if result.content is not None:
        ext = ".png" if result.mime_type and "png" in result.mime_type else ".jpg"
        return store_bytes(
            content=result.content,
            subdir=subdir,
            filename=f"{stem}{ext}",
            settings=settings,
            content_type=result.mime_type,
        )
    if result.url:
        _, stored = await download_media_url(
            url=result.url,
            settings=settings,
            subdir=subdir,
            stem=stem,
            fallback_extension=".jpg",
            max_bytes=25 * 1024 * 1024,
        )
        return stored
    raise ImageProviderError("Generated image has no URL or bytes to store")
