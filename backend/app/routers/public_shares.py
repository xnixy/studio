"""Public share link view/unlock (no agency client graph)."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.media_signing import SHARE_MEDIA_TTL_SECONDS, sign_media_fields
from app.models import ShareLink
from app.rate_limit_deps import rate_limit_ip
from app.schemas import ShareLinkPublicDto, ShareLinkUnlockRequest
from app.security import verify_password

router = APIRouter(tags=["public"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _sign_snapshot(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    settings = get_settings()
    raw = dict(snapshot or {})
    signed = sign_media_fields(raw, settings, ttl_seconds=SHARE_MEDIA_TTL_SECONDS)
    for nest_key in ("render", "asset", "voiceover", "project", "media"):
        if isinstance(signed.get(nest_key), dict):
            signed[nest_key] = sign_media_fields(signed[nest_key], settings, ttl_seconds=SHARE_MEDIA_TTL_SECONDS)
    items = signed.get("items")
    if isinstance(items, list):
        signed["items"] = [
            sign_media_fields(item, settings, ttl_seconds=SHARE_MEDIA_TTL_SECONDS) if isinstance(item, dict) else item
            for item in items
        ]
    return signed


@router.get("/public/shares/{token}", response_model=ShareLinkPublicDto)
async def public_share_view(
    token: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ShareLinkPublicDto:
    await rate_limit_ip(request, "share.view", 60, 15 * 60, "Too many share requests. Please try again later.")
    link = await session.scalar(select(ShareLink).where(ShareLink.token_hash == _token_hash(token)))
    if link is None or link.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if link.expires_at is not None and link.expires_at < _utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")
    requires_password = bool(link.password_hash)
    if not requires_password:
        link.view_count += 1
        link.last_viewed_at = _utcnow()
        await session.commit()
        return ShareLinkPublicDto(
            title=link.title,
            resource_type=link.resource_type,  # type: ignore[arg-type]
            allow_download=link.allow_download,
            snapshot=_sign_snapshot(dict(link.snapshot or {})),
            requires_password=False,
        )
    return ShareLinkPublicDto(
        title=link.title,
        resource_type=link.resource_type,  # type: ignore[arg-type]
        allow_download=link.allow_download,
        snapshot={},
        requires_password=True,
    )


@router.post("/public/shares/{token}/unlock", response_model=ShareLinkPublicDto)
async def public_share_unlock(
    token: str,
    payload: ShareLinkUnlockRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ShareLinkPublicDto:
    await rate_limit_ip(
        request,
        "share.unlock",
        20,
        15 * 60,
        "Too many share unlock attempts.",
        require_redis=True,
    )
    link = await session.scalar(select(ShareLink).where(ShareLink.token_hash == _token_hash(token)))
    if link is None or link.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")
    if link.expires_at is not None and link.expires_at < _utcnow():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Share link expired")
    if not link.password_hash or not verify_password(payload.password, link.password_hash):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid share password")
    link.view_count += 1
    link.last_viewed_at = _utcnow()
    await session.commit()
    return ShareLinkPublicDto(
        title=link.title,
        resource_type=link.resource_type,  # type: ignore[arg-type]
        allow_download=link.allow_download,
        snapshot=_sign_snapshot(dict(link.snapshot or {})),
        requires_password=False,
    )
