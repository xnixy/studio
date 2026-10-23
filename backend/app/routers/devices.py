"""Mobile device registration (Expo push tokens)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.models.devices import DevicePushToken
from app.schemas import MessageResponse

router = APIRouter(prefix="/devices", tags=["devices"])


class PushTokenRequest(BaseModel):
    token: str = Field(min_length=10, max_length=512)
    platform: str = Field(default="ios", max_length=16)
    """Stable per-install id so a phone replaces its own row instead of adding one."""
    device_id: str | None = Field(default=None, max_length=128)


@router.post("/push-token", response_model=MessageResponse)
async def register_push_token(
    payload: PushTokenRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    token = payload.token.strip()
    platform = (payload.platform or "ios").strip().lower()[:16]
    device_id = (payload.device_id or "").strip()[:128] or None
    now = datetime.now(timezone.utc)

    existing = await session.scalar(select(DevicePushToken).where(DevicePushToken.token == token))
    if existing:
        if existing.user_id != user.id:
            # Do not reassign another user's push token (notification hijack).
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This push token is already registered to another account",
            )
        existing.platform = platform
        if device_id:
            existing.device_id = device_id
        existing.updated_at = now
        await session.commit()
        return MessageResponse(message="Push token registered")

    if device_id:
        # This phone already has a row; Expo rotated its token. Move the row rather
        # than adding one, or the device is notified once per token it ever held.
        for_device = await session.scalar(
            select(DevicePushToken).where(
                DevicePushToken.user_id == user.id,
                DevicePushToken.device_id == device_id,
            )
        )
        if for_device is not None:
            for_device.token = token
            for_device.platform = platform
            for_device.updated_at = now
            await session.commit()
            return MessageResponse(message="Push token registered")

    session.add(
        DevicePushToken(
            user_id=user.id,
            token=token,
            platform=platform,
            device_id=device_id,
            created_at=now,
            updated_at=now,
        )
    )
    await session.commit()
    return MessageResponse(message="Push token registered")


@router.delete("/push-token", response_model=MessageResponse)
async def unregister_push_token(
    payload: PushTokenRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    existing = await session.scalar(
        select(DevicePushToken).where(
            DevicePushToken.token == payload.token.strip(),
            DevicePushToken.user_id == user.id,
        )
    )
    if existing:
        await session.delete(existing)
        await session.commit()
    return MessageResponse(message="Push token removed")
