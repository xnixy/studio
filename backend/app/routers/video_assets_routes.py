"""Video asset poll (Play generation status)."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_current_user
from app.models import User
from app.provider_errors import http_provider_exception
from app.routers.video_helpers import get_asset, map_asset
from app.schemas import VideoAssetDto
from app.video_asset_poll import VideoAssetPollError, poll_and_update_asset

router = APIRouter(tags=["video"])


@router.post("/assets/{asset_id}/poll", response_model=VideoAssetDto)
async def poll_video_asset(
    asset_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> VideoAssetDto:
    asset = await get_asset(asset_id, user, session, "projects.write")

    # A worker job owns polling for this asset in production. Two pollers writing
    # the same row can land a stale tick on top of a finished one, flipping a
    # ready clip back to processing. Report current state instead of racing it.
    #
    # Only while that job is actually live, though. A job stranded by a dead
    # worker never advances the asset, and the tick budget and stuck-asset sweep
    # that would fail-and-refund it both run in the same worker — so deferring to
    # it unconditionally turns a worker outage into a clip that spins forever.
    # Past the grace window there is no one to race, so the client poll takes over.
    if asset.status not in {"ready", "failed", "expired"}:
        from sqlalchemy import select

        from app.job_queue import job_is_abandoned
        from app.models import BackgroundJob

        live_job = await session.scalar(
            select(BackgroundJob).where(
                BackgroundJob.idempotency_key == f"video.asset.poll:{asset.id}",
                BackgroundJob.status.in_(("queued", "running", "waiting_for_provider")),
            )
        )
        if live_job is not None and not job_is_abandoned(live_job):
            return map_asset(asset)

    try:
        asset = await poll_and_update_asset(
            session,
            asset,
            settings,
            actor_user_id=user.id,
            commit=True,
            emit_events=True,
        )
    except VideoAssetPollError as exc:
        if exc.cause is not None:
            raise http_provider_exception(exc.cause, kind="media") from exc.cause
        raise HTTPException(status_code=exc.http_status, detail=str(exc)) from exc
    return map_asset(asset)
