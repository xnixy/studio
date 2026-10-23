from __future__ import annotations

import subprocess

from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models import MaintenanceSetting, User
from app.schemas import FfmpegStatusDto, MaintenanceStatus, PublicConfigDto, TtsStatusDto
from app.turnstile import turnstile_public_config
from app.video_renderer import ffmpeg_path

router = APIRouter(tags=["system"])


@router.get("/public-config", response_model=PublicConfigDto)
async def public_config(settings: Settings = Depends(get_settings)) -> PublicConfigDto:
    """Public client config (Turnstile site key). No secrets."""
    return PublicConfigDto(**turnstile_public_config(settings))


@router.get("/health")
async def health(request: Request, session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    """Liveness-style probe. In production, Redis is required (auth fail-closed)."""
    from fastapi.responses import JSONResponse

    checks: dict[str, str] = {}
    ok = True

    try:
        await session.execute(text("select 1"))
        checks["postgres"] = "healthy"
    except Exception:
        checks["postgres"] = "unhealthy"
        ok = False

    limiter = getattr(request.app.state, "rate_limiter", None)
    redis_client = getattr(limiter, "redis", None) if limiter is not None else None
    if redis_client is None:
        checks["redis"] = "not_configured_or_fallback"
        if settings_is_production(request):
            ok = False
    else:
        try:
            await redis_client.ping()
            checks["redis"] = "healthy"
        except Exception:
            checks["redis"] = "unhealthy"
            ok = False

    checks["ffmpeg"] = "healthy" if ffmpeg_path() else "missing"

    body = {"status": "healthy" if ok else "degraded", "checks": checks}
    if not ok:
        return JSONResponse(body, status_code=503)
    return body


def settings_is_production(request: Request) -> bool:
    settings = get_settings()
    return settings.is_production


@router.get("/maintenance", response_model=MaintenanceStatus)
async def get_maintenance(session: AsyncSession = Depends(get_session)) -> MaintenanceStatus:
    setting = await session.get(MaintenanceSetting, 1)
    return MaintenanceStatus(enabled=setting.enabled if setting else False, message=setting.message if setting else None)


@router.get("/tts/status", response_model=TtsStatusDto)
async def tts_status(
    _: User = Depends(get_current_user),
    settings: Settings = Depends(get_settings),
) -> TtsStatusDto:
    return TtsStatusDto(
        xai_api_key_configured=bool(settings.xai_api_key),
        tts_url=settings.xai_tts_url,
        media_dir=str(settings.media_path),
        media_backend="r2" if settings.r2_enabled else "local",
        media_public_base_url=settings.media_public_base_url,
    )


@router.get("/render/status", response_model=FfmpegStatusDto)
async def render_status(_: User = Depends(get_current_user)) -> FfmpegStatusDto:
    path = ffmpeg_path()
    if not path:
        return FfmpegStatusDto(available=False)
    try:
        result = subprocess.run([path, "-version"], capture_output=True, check=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return FfmpegStatusDto(available=False, path=path)
    first_line = result.stdout.splitlines()[0] if result.stdout else None
    return FfmpegStatusDto(available=True, path=path, version=first_line)
