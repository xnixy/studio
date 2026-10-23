from __future__ import annotations

"""Video API: provider status + asset poll used by Play."""

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.media_store import r2_enabled
from app.schemas import VideoProviderStatusDto, VideoSystemStatusDto
from app.video_renderer import ffmpeg_path
from app.routers.video_helpers import provider_status
from app.routers import video_assets_routes

router = APIRouter(prefix="/video", tags=["video"])


@router.get("/providers/status", response_model=VideoSystemStatusDto)
async def video_provider_status(
    settings: Settings = Depends(get_settings),
) -> VideoSystemStatusDto:
    path = ffmpeg_path()
    return VideoSystemStatusDto(
        ffmpeg_available=bool(path),
        ffmpeg_path=path,
        public_api_base_url=settings.public_api_base_url,
        media_base_url=settings.media_public_base_url,
        media_backend="r2" if r2_enabled(settings) else "local",
        providers=[
            provider_status(
                "xai_image",
                bool(settings.xai_api_key),
                settings.xai_image_model,
                "xAI image generation is configured.",
                "Set XAI_API_KEY to generate scene images.",
            ),
            provider_status(
                "xai_video",
                bool(settings.xai_api_key),
                settings.xai_video_model,
                "xAI video generation is configured.",
                "Set XAI_API_KEY to generate and extend scene video.",
            ),
            provider_status(
                "gemini_image",
                bool(settings.gemini_api_key),
                settings.gemini_image_model,
                "Google Nano Banana image generation is configured.",
                "Set GEMINI_API_KEY for Nano Banana stills.",
            ),
            provider_status(
                "gemini_video",
                bool(settings.gemini_api_key),
                settings.gemini_video_model,
                "Google Veo video generation is configured.",
                "Set GEMINI_API_KEY for Veo clips.",
            ),
            provider_status(
                "sync_labs",
                bool(settings.sync_labs_api_key),
                settings.sync_labs_model,
                "Sync Labs avatar lip-sync is configured.",
                "Set SYNC_LABS_API_KEY to enable avatar lip-sync.",
            ),
            provider_status(
                "cloudflare_r2",
                r2_enabled(settings),
                settings.r2_bucket_name,
                "Cloudflare R2 durable media storage is configured.",
                "Set R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, and R2_BUCKET_NAME for durable media.",
            ),
        ],
    )


router.include_router(video_assets_routes.router)
