"""Background poll for Play video assets until ready/failed."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.config import get_settings
from app.jobs.base import JobContext, JobDeferred
from app.models import VideoAsset
from app.video_asset_poll import (
    VideoAssetPollError,
    emit_asset_terminal,
    poll_and_update_asset,
    release_usage_for_failed_asset,
)

# Soft ticks before we fail the asset (worker keeps requeueing without burning max_attempts).
MAX_POLL_TICKS = 90  # ~12–20 min depending on delay
BASE_DELAY_SECONDS = 8
MAX_DELAY_SECONDS = 20


class VideoAssetPollHandler:
    job_type = "video.asset.poll"

    async def run(self, ctx: JobContext) -> dict[str, Any]:
        payload = dict(ctx.job.payload or {})
        raw_id = payload.get("asset_id")
        if not raw_id:
            raise ValueError("video.asset.poll requires payload.asset_id")
        asset_id = UUID(str(raw_id))
        asset = await ctx.session.get(VideoAsset, asset_id)
        if asset is None:
            return {"ok": False, "reason": "asset_missing"}
        if asset.workspace_id != ctx.workspace_id:
            raise ValueError("asset workspace mismatch")

        if asset.status in {"ready", "failed", "expired"}:
            # Ready clips still need the repair pass (clip poster + moov-at-start).
            # poll_and_update_asset short-circuits on terminal status and repairs
            # there, so queueing a poll is how older clips get fixed.
            if asset.status == "ready" and asset.asset_type == "video":
                await poll_and_update_asset(
                    ctx.session,
                    asset,
                    get_settings(),
                    actor_user_id=ctx.job.created_by_id,
                    commit=True,
                    emit_events=False,
                )
                await ctx.session.refresh(asset)
                meta = dict(asset.asset_metadata or {})
                return {
                    "ok": True,
                    "status": asset.status,
                    "asset_id": str(asset.id),
                    "faststart": bool(meta.get("faststart")),
                    "clip_poster": bool(meta.get("clip_poster")),
                }
            return {"ok": True, "status": asset.status, "asset_id": str(asset.id)}

        ticks = int(payload.get("poll_ticks") or 0)
        if ticks >= MAX_POLL_TICKS:
            asset.status = "failed"
            asset.error_message = (
                asset.error_message
                or "Generation timed out after extended polling. Try again or open Library later."
            )
            # Timeout is a terminal failure like any other: refund the reserved
            # tokens and tell the user, instead of silently keeping both.
            await release_usage_for_failed_asset(ctx.session, asset)
            await ctx.session.commit()
            await emit_asset_terminal(ctx.session, asset, actor_user_id=ctx.job.created_by_id)
            return {"ok": False, "status": "failed", "reason": "poll_budget_exceeded"}

        settings = get_settings()
        actor_id = ctx.job.created_by_id
        try:
            await poll_and_update_asset(
                ctx.session,
                asset,
                settings,
                actor_user_id=actor_id,
                commit=True,
                emit_events=True,
            )
        except VideoAssetPollError:
            # Failed status already committed inside poll helper when provider errors.
            await ctx.session.refresh(asset)
            if asset.status == "failed":
                return {"ok": False, "status": "failed", "asset_id": str(asset.id)}
            # Transient config/network — soft defer.
            delay = min(MAX_DELAY_SECONDS, BASE_DELAY_SECONDS + ticks // 5)
            raise JobDeferred(
                delay,
                result={"status": asset.status, "asset_id": str(asset.id), "tick": ticks + 1},
            ) from None

        await ctx.session.refresh(asset)
        if asset.status in {"ready", "failed", "expired"}:
            return {"ok": True, "status": asset.status, "asset_id": str(asset.id), "tick": ticks + 1}

        delay = min(MAX_DELAY_SECONDS, BASE_DELAY_SECONDS + ticks // 5)
        raise JobDeferred(
            delay,
            result={"status": asset.status, "asset_id": str(asset.id), "tick": ticks + 1},
        )
