"""Shared rate-limit helpers for route handlers."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.config import get_settings
from app.dependencies import get_client_ip
from app.rate_limit import RateLimiter


async def enforce_rate_limit(
    request: Request,
    key: str,
    limit: int,
    window_seconds: int,
    message: str,
    *,
    require_redis: bool | None = None,
) -> None:
    """Apply a rate limit. Auth-sensitive callers should set require_redis=True in production."""
    limiter: RateLimiter = request.app.state.rate_limiter
    settings = get_settings()
    # In production, fail closed when Redis is down for keys that opt in.
    if require_redis is None:
        require_redis = False
    if require_redis and settings.is_production and not limiter.using_redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again shortly.",
        )
    allowed = await limiter.hit(key, limit, window_seconds, require_redis=bool(require_redis and settings.is_production))
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message)


async def rate_limit_ip(
    request: Request,
    bucket: str,
    limit: int,
    window_seconds: int,
    message: str | None = None,
    *,
    require_redis: bool = False,
) -> None:
    ip = get_client_ip(request)
    await enforce_rate_limit(
        request,
        f"{bucket}:{ip}",
        limit,
        window_seconds,
        message or "Too many requests. Please try again later.",
        require_redis=require_redis,
    )


async def rate_limit_user(request: Request, bucket: str, user_id: str, limit: int, window_seconds: int) -> None:
    await enforce_rate_limit(
        request,
        f"{bucket}:user:{user_id}",
        limit,
        window_seconds,
        "Rate limit exceeded. Please slow down and try again.",
    )
