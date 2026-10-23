"""Shared Play/video asset provider polling (HTTP route + job worker)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.gemini_video import GeminiVideoError, download_gemini_video_url, poll_gemini_video
from app.kling_media import KlingMediaError, kling_configured, poll_kling_video
from app.media_store import store_bytes
from app.models import AuditEvent, UsageEvent, User, VideoAsset
from app.provider_errors import http_provider_exception, public_error_message, public_status_message
from app.routers.video_helpers import add_generation_cost, maybe_auto_persist_asset, sync_asset_status
from app.seedance_media import SeedanceMediaError, poll_seedance_video
from app.sync_labs import SyncLabsError, poll_sync_labs_generation
from app.xai_media import XaiMediaError, poll_xai_video


class VideoAssetPollError(RuntimeError):
    """Provider/config error while polling; may map to HTTP."""

    def __init__(self, message: str, *, http_status: int = 502, cause: Exception | None = None):
        super().__init__(message)
        self.http_status = http_status
        self.cause = cause


def _is_retriable_config_error(exc: BaseException) -> bool:
    """True when the worker/API is misconfigured, not when the provider rejected the job.

    These should soft-defer (job) or 503 (HTTP) without marking the asset failed —
    the upstream generation may still be running.
    """
    text = str(exc).lower()
    if "not configured" in text or "is not configured" in text:
        return True
    # Auth to our provider account is an ops issue; do not burn the clip.
    if any(
        needle in text
        for needle in (
            "invalid api key",
            "incorrect api key",
            "api key not valid",
            "authentication",
            "unauthorized",
            "http 401",
            "http 403",
        )
    ):
        # Spend/credit limits are real terminal-ish provider states — fail those.
        if "credits" in text or "spending limit" in text or "permission-denied" in text:
            return False
        return True
    return False


async def _generation_cost_recorded(session: AsyncSession, asset: VideoAsset) -> bool:
    """True when this generation already has a poll cost row.

    Guards against the worker job and a client HTTP poll both recording the
    provider cost for one clip.
    """
    from sqlalchemy import select

    from app.models import GenerationCost

    if not asset.provider_request_id:
        return False
    existing = await session.scalar(
        select(GenerationCost.id).where(
            GenerationCost.provider_request_id == asset.provider_request_id,
            GenerationCost.feature == "video_asset_poll",
        )
    )
    return existing is not None


def _clip_href(asset: VideoAsset) -> str:
    return f"/clips/{asset.id}"


# Anything non-terminal past this age has no live poll job: the tick budget in
# app/jobs/video_asset_poll.py tops out around 30 minutes end to end.
STUCK_ASSET_MAX_AGE_SECONDS = 45 * 60


async def fail_stuck_processing_assets(
    session: AsyncSession,
    *,
    max_age_seconds: int = STUCK_ASSET_MAX_AGE_SECONDS,
    limit: int = 25,
) -> int:
    """Fail and refund assets stuck non-terminal past the ceiling.

    Safety net for polls that died outside the tick budget: worker crash after
    claim, enqueue dropped on the floor, or repeated transient errors burning
    the job's attempts. Without this the clip spins in Clips forever and the
    reservation stays consumed.
    """
    from datetime import timedelta

    from sqlalchemy import select

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)
    assets = (
        await session.scalars(
            select(VideoAsset)
            .where(
                VideoAsset.status.in_(("queued", "processing")),
                VideoAsset.updated_at < cutoff,
            )
            .with_for_update(skip_locked=True)
            .limit(limit)
        )
    ).all()
    failed = 0
    for asset in assets:
        asset.status = "failed"
        asset.error_message = (
            asset.error_message
            or "Generation stalled and was closed out. Your credits were returned."
        )
        await release_usage_for_failed_asset(session, asset)
        failed += 1
    if failed:
        await session.commit()
        for asset in assets:
            await emit_asset_terminal(session, asset, actor_user_id=None)
    return failed


async def release_usage_for_failed_asset(session: AsyncSession, asset: VideoAsset) -> None:
    """Release linked usage events when an async generation fails or expires.

    Prefers ``usage_event_ids`` on asset metadata. Falls back to usage rows whose
    metadata references this asset_id (older rows missing the link). Idempotent
    via ``usage_refunded``. Does not commit; caller owns the transaction.
    """
    from sqlalchemy import select

    meta = dict(asset.asset_metadata or {})
    if meta.get("usage_refunded"):
        return

    event_ids: list[UUID] = []
    raw_ids = meta.get("usage_event_ids")
    if isinstance(raw_ids, list):
        for raw in raw_ids:
            try:
                event_ids.append(UUID(str(raw)))
            except (TypeError, ValueError):
                continue

    # Fallback: match by asset_id stamped in reservation metadata.
    if not event_ids:
        asset_key = str(asset.id)
        rows = (
            await session.scalars(
                select(UsageEvent).where(
                    UsageEvent.workspace_id == asset.workspace_id,
                    UsageEvent.status.in_(("reserved", "consumed")),
                )
            )
        ).all()
        for event in rows:
            em = dict(event.event_metadata or {})
            if str(em.get("asset_id") or "") == asset_key:
                event_ids.append(event.id)
                continue
            # Older start path only stored model/token without asset_id; match
            # same-second orphans only when provider request is known is too risky.
            # Prefer explicit usage_event_ids going forward.

    if not event_ids:
        return

    released_any = False
    for event_id in event_ids:
        event = await session.get(UsageEvent, event_id)
        if event is None:
            continue
        if event.status not in {"consumed", "reserved"}:
            continue
        event.status = "released"
        event.event_metadata = {
            **dict(event.event_metadata or {}),
            "refunded_reason": "async_generation_failed",
            "refunded_asset_id": str(asset.id),
        }
        released_any = True

    if released_any:
        meta["usage_refunded"] = True
        if not isinstance(meta.get("usage_event_ids"), list):
            meta["usage_event_ids"] = [str(i) for i in event_ids]
        asset.asset_metadata = meta


async def emit_asset_terminal(
    session: AsyncSession,
    asset: VideoAsset,
    *,
    actor_user_id: UUID | None,
) -> None:
    if asset.status not in {"ready", "failed"}:
        return
    try:
        from app.events.emit import emit_domain_event

        await emit_domain_event(
            session,
            type="video.asset.ready" if asset.status == "ready" else "video.asset.failed",
            workspace_id=asset.workspace_id,
            actor_user_id=actor_user_id,
            entity_kind="video_asset",
            entity_id=asset.id,
            title="Video clip ready" if asset.status == "ready" else "Video generation failed",
            body=None if asset.status == "ready" else (asset.error_message or "Generation failed"),
            href=_clip_href(asset),
            payload={"status": asset.status, "asset_type": asset.asset_type, "asset_id": str(asset.id)},
            recipient_mode="workspace_members",
            dedupe_key=f"video_asset:{asset.id}:{asset.status}",
            commit=True,
        )
    except Exception:
        pass


async def poll_and_update_asset(
    session: AsyncSession,
    asset: VideoAsset,
    settings: Settings,
    *,
    actor_user_id: UUID | None = None,
    commit: bool = True,
    emit_events: bool = True,
) -> VideoAsset:
    """One provider status tick. Updates asset in place. Short-circuits if already terminal."""
    if asset.status in {"ready", "failed", "expired"}:
        # Repair pass for ready videos: clip poster (list thumbs must not show the
        # face plate) and moov-at-start (iOS cannot progressive-stream without it).
        # Runs wherever the poll runs, so queueing a poll repairs older clips.
        if asset.status == "ready" and asset.asset_type == "video":
            from app.routers.video_helpers import ensure_asset_streamable, maybe_attach_clip_poster

            meta = dict(asset.asset_metadata or {})
            changed = False
            if not meta.get("clip_poster"):
                maybe_attach_clip_poster(asset, settings)
                changed = bool(dict(asset.asset_metadata or {}).get("clip_poster"))
            if not dict(asset.asset_metadata or {}).get("faststart"):
                # Always a metadata write (faststart or faststart_error), so keep it.
                ensure_asset_streamable(asset, settings)
                changed = True
            if commit and changed:
                await session.commit()
                await session.refresh(asset)
        return asset

    if not asset.provider_request_id:
        raise VideoAssetPollError(
            "Asset does not have a provider request to poll",
            http_status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    previous_status = asset.status
    provider = (asset.provider or "").strip().lower()

    try:
        if provider == "sync_labs":
            await _poll_sync_labs(session, asset, settings)
        elif provider == "gemini":
            await _poll_gemini(session, asset, settings)
        elif provider == "kling":
            await _poll_kling(session, asset, settings)
        elif provider == "seedance":
            await _poll_seedance(session, asset, settings)
        else:
            await _poll_xai(session, asset, settings, actor_user_id=actor_user_id)
    except (SyncLabsError, GeminiVideoError, KlingMediaError, SeedanceMediaError, XaiMediaError) as exc:
        raw = str(exc)[:500]
        print(
            f"video_asset_poll provider_fail asset={asset.id} provider={provider} "
            f"raw={raw!r}",
            flush=True,
        )
        # Missing keys / local config must not kill an in-flight provider job.
        # Workers without secrets (or shared Neon + under-configured Fly) would
        # otherwise mark good generations failed with "isn't available".
        if _is_retriable_config_error(exc):
            asset.asset_metadata = {
                **dict(asset.asset_metadata or {}),
                "last_poll_config_error": raw,
                "last_poll_config_error_type": type(exc).__name__,
            }
            if commit:
                await session.commit()
            raise VideoAssetPollError(
                public_error_message(exc, kind="media"),
                http_status=503,
                cause=exc,
            ) from exc

        asset.status = "failed"
        asset.error_message = public_error_message(exc, kind="media")
        asset.asset_metadata = {
            **dict(asset.asset_metadata or {}),
            "provider_error_raw": raw,
            "provider_error_type": type(exc).__name__,
        }
        await release_usage_for_failed_asset(session, asset)
        if commit:
            await session.commit()
            if emit_events:
                await emit_asset_terminal(session, asset, actor_user_id=actor_user_id)
        raise VideoAssetPollError(str(asset.error_message), cause=exc) from exc

    # Refund tokens when generation ends in a terminal failure/expiry.
    if asset.status in {"failed", "expired"} and previous_status not in {"failed", "expired"}:
        await release_usage_for_failed_asset(session, asset)

    if asset.status != previous_status and actor_user_id is not None:
        session.add(
            AuditEvent(
                workspace_id=asset.workspace_id,
                actor_id=actor_user_id,
                action="video_asset.status_changed",
                details={"asset_id": str(asset.id), "status": asset.status},
            )
        )

    if commit:
        await session.commit()
        if emit_events and asset.status != previous_status:
            await emit_asset_terminal(session, asset, actor_user_id=actor_user_id)
        await session.refresh(asset)
    return asset


async def _poll_sync_labs(session: AsyncSession, asset: VideoAsset, settings: Settings) -> None:
    if not settings.sync_labs_api_key:
        raise VideoAssetPollError("Sync Labs API key is not configured", http_status=503)
    result = await poll_sync_labs_generation(asset.provider_request_id or "", settings)
    asset.status = sync_asset_status(result.status)
    asset.provider_model = result.model
    asset.provider_url = result.output_url
    asset.error_message = (
        public_status_message(
            result.error_message, fallback=f"Sync Labs generation {result.status.lower()}"
        )
        if asset.status == "failed"
        else result.error_message
    )
    asset.asset_metadata = {
        **dict(asset.asset_metadata or {}),
        "provider_status": result.status,
        "duration_seconds": result.duration_seconds,
        "provider_response": result.raw,
        "provider_error_code": result.raw.get("errorCode") if isinstance(result.raw, dict) else None,
    }
    if asset.status == "ready":
        await maybe_auto_persist_asset(asset, settings)
    if asset.status == "processing" and asset.created_at:
        created_at = asset.created_at if asset.created_at.tzinfo else asset.created_at.replace(tzinfo=timezone.utc)
        if (datetime.now(timezone.utc) - created_at).total_seconds() >= 600:
            asset.status = "failed"
            asset.error_message = (
                "Sync Labs did not start this job within 10 minutes. The request may have been created "
                "without sufficient provider credits. Credits added later may not revive it; generate a new lip-sync clip."
            )


async def _poll_gemini(session: AsyncSession, asset: VideoAsset, settings: Settings) -> None:
    if not settings.gemini_api_key:
        raise VideoAssetPollError("Gemini API key is not configured", http_status=503)
    g_result = await poll_gemini_video(asset.provider_request_id or "", settings)
    if g_result.status == "done" and g_result.url:
        asset.status = "ready"
        asset.error_message = None
        # Only download once; later ticks must not re-fetch multi-MB MP4s (client timeouts).
        if not asset.storage_url:
            try:
                content = await download_gemini_video_url(g_result.url, settings)
                stored = store_bytes(
                    content=content,
                    subdir="play",
                    filename=f"{asset.id}.mp4",
                    settings=settings,
                    content_type="video/mp4",
                )
                asset.storage_url = stored
                asset.provider_url = stored
            except Exception as persist_exc:  # noqa: BLE001
                asset.provider_url = g_result.url
                asset.asset_metadata = {
                    **dict(asset.asset_metadata or {}),
                    "persist_error": str(persist_exc)[:240],
                    "gemini_video_uri": g_result.url,
                }
    elif g_result.status == "failed":
        asset.status = "failed"
        asset.error_message = public_status_message(
            g_result.error_message, fallback="Gemini video failed"
        )
    else:
        asset.status = "processing"

    asset.asset_metadata = {
        **dict(asset.asset_metadata or {}),
        "provider_status": g_result.status,
        "provider_response": g_result.raw,
    }
    if asset.status == "ready":
        await maybe_auto_persist_asset(asset, settings)


async def _poll_kling(session: AsyncSession, asset: VideoAsset, settings: Settings) -> None:
    if not kling_configured(settings):
        raise VideoAssetPollError("Kling API key is not configured", http_status=503)
    meta = dict(asset.asset_metadata or {})
    endpoint = meta.get("kling_endpoint")
    ep = endpoint if isinstance(endpoint, str) else None
    k_result = await poll_kling_video(asset.provider_request_id or "", settings, endpoint=ep)
    if k_result.status == "done" and k_result.url:
        asset.status = "ready"
        asset.provider_url = k_result.url
        asset.error_message = None
    elif k_result.status == "failed":
        asset.status = "failed"
        asset.error_message = public_status_message(
            k_result.error_message, fallback="Kling generation failed"
        )
    else:
        asset.status = "processing"
    if k_result.model:
        asset.provider_model = k_result.model
    meta_extra: dict = {
        "provider_status": k_result.status,
        "provider_response": k_result.raw,
    }
    if k_result.duration is not None:
        meta_extra["duration_seconds"] = k_result.duration
    asset.asset_metadata = {**dict(asset.asset_metadata or {}), **meta_extra}
    if asset.status == "ready":
        await maybe_auto_persist_asset(asset, settings)


async def _poll_seedance(session: AsyncSession, asset: VideoAsset, settings: Settings) -> None:
    if not settings.seedance_api_key:
        raise VideoAssetPollError("Seedance API key is not configured", http_status=503)
    s_result = await poll_seedance_video(asset.provider_request_id or "", settings)
    if s_result.status == "done" and s_result.url:
        asset.status = "ready"
        asset.provider_url = s_result.url
        asset.error_message = None
    elif s_result.status == "failed":
        asset.status = "failed"
        asset.error_message = public_status_message(
            s_result.error_message, fallback="Seedance generation failed"
        )
    else:
        asset.status = "processing"
    if s_result.model:
        asset.provider_model = s_result.model
    meta_extra: dict = {
        "provider_status": s_result.status,
        "provider_response": s_result.raw,
    }
    if s_result.duration is not None:
        meta_extra["duration_seconds"] = s_result.duration
    if s_result.last_frame_url:
        meta_extra["last_frame_url"] = s_result.last_frame_url
        meta_extra["poster_url"] = s_result.last_frame_url
        meta_extra["clip_poster"] = True
        meta_extra["clip_poster_url"] = s_result.last_frame_url
        if asset.status == "ready":
            try:
                from app.media_store import download_media_url

                _path, stored_poster = await download_media_url(
                    url=s_result.last_frame_url,
                    settings=settings,
                    subdir="play",
                    stem=f"{asset.id}-last",
                    fallback_extension=".jpg",
                )
                if stored_poster:
                    meta_extra["poster_url"] = stored_poster
                    meta_extra["last_frame_url"] = stored_poster
                    meta_extra["clip_poster_url"] = stored_poster
                    meta_extra["clip_poster"] = True
            except Exception:
                pass
    asset.asset_metadata = {**dict(asset.asset_metadata or {}), **meta_extra}
    if asset.status == "ready":
        await maybe_auto_persist_asset(asset, settings)


async def _poll_xai(
    session: AsyncSession,
    asset: VideoAsset,
    settings: Settings,
    *,
    actor_user_id: UUID | None,
) -> None:
    if not settings.xai_api_key:
        raise VideoAssetPollError("xAI API key is not configured", http_status=503)
    result = await poll_xai_video(asset.provider_request_id or "", settings)
    if result.status == "done":
        asset.provider_url = result.url
        asset.error_message = None
        pending_voice = dict(asset.asset_metadata or {}).get("voice_pass") == "pending"
        if not pending_voice:
            asset.status = "ready"
    elif result.status == "expired":
        asset.status = "expired"
        asset.error_message = public_status_message(
            result.error_message, fallback="Provider generation expired"
        )
    elif result.status == "failed":
        asset.status = "failed"
        asset.error_message = public_status_message(
            result.error_message, fallback="Provider generation failed"
        )
    else:
        asset.status = "processing"
    asset.provider_model = result.model
    # cost_usd_ticks alone is an in-memory guard: two pollers that both loaded a
    # null cost would each insert a row for one generation. Check what is stored.
    if result.cost_usd_ticks is not None and asset.cost_usd_ticks is None:
        asset.cost_usd_ticks = result.cost_usd_ticks
        if not await _generation_cost_recorded(session, asset):
            add_generation_cost(
                session,
                workspace_id=asset.workspace_id,
                user_id=actor_user_id,
                feature="video_asset_poll",
                provider_model=result.model,
                provider_request_id=asset.provider_request_id,
                cost_usd_ticks=result.cost_usd_ticks,
                metadata={"asset_id": str(asset.id), "provider_status": result.status},
            )
    meta_next = {
        **dict(asset.asset_metadata or {}),
        "provider_status": result.status,
        "provider_response": result.raw,
    }
    # Do not clobber the request duration with a null provider field while pending.
    if result.duration is not None:
        meta_next["duration_seconds"] = result.duration
    asset.asset_metadata = meta_next
    if result.status == "done" and dict(meta_next).get("voice_pass") == "pending":
        from app.routers.play_talking_clone import continue_talking_clone_voice_pass

        await continue_talking_clone_voice_pass(session, asset, settings)
        return
    if asset.status == "ready":
        await maybe_auto_persist_asset(asset, settings)
