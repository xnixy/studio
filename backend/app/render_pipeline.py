"""FFmpeg concat render for multi-scene video projects.

Legacy AdConcept / concept-voiceover coupling is gone. Play stores audio on
scene assets (or provider audio). Captions use scene spoken/on-screen text.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.media_store import MediaStoreError, download_media_url
from app.models import AuditEvent, CaptionTrack, VideoRender
from app.video_renderer import VideoRenderError, ready_scene_video_assets, render_concat_mp4, write_caption_sidecars

logger = logging.getLogger(__name__)


async def process_render_pipeline(
    *,
    render: VideoRender,
    session: AsyncSession,
    settings: Settings,
    actor_id: UUID | None,
) -> VideoRender:
    render.status = "rendering"
    job = sorted(render.jobs, key=lambda item: item.created_at, reverse=True)[0] if render.jobs else None
    if job is not None:
        job.status = "rendering"
        job.attempts += 1
    await session.flush()
    try:
        from app.events.render_bridge import publish_render_status

        await publish_render_status(
            workspace_id=render.workspace_id,
            render_id=render.id,
            status="rendering",
            video_project_id=render.video_project_id,
        )
    except Exception:
        logger.warning("render status publish failed render_id=%s", render.id, exc_info=True)

    try:
        for asset in ready_scene_video_assets(render.project):
            if asset.storage_url or not asset.provider_url:
                continue
            _, storage_url = await download_media_url(
                url=asset.provider_url,
                settings=settings,
                subdir="video-assets",
                stem=asset.id,
                fallback_extension=".mp4",
            )
            asset.storage_url = storage_url
            asset.asset_metadata = {**dict(asset.asset_metadata or {}), "persisted_by_render": str(render.id)}
        # Scene timeline captions only (no concept-linked VO path).
        _, output_url, captions_burned_in, sync_metadata = render_concat_mp4(
            render.project,
            render,
            settings,
            audio_path=None,
            caption_override_rows=None,
        )
        sidecar_urls = write_caption_sidecars(render.project, render, settings, rows=None)
        sync_metadata = {
            **sync_metadata,
            "caption_timing_source": "scene_timeline",
            "audio_mixed": False,
        }
    except (MediaStoreError, VideoRenderError) as exc:
        render.status = "failed"
        render.error_message = str(exc)
        if job is not None:
            job.status = "failed"
            job.error_message = str(exc)
        session.add(
            AuditEvent(
                workspace_id=render.workspace_id,
                actor_id=actor_id,
                action="video_render.failed",
                details={"render_id": str(render.id), "error": str(exc)[:300]},
            )
        )
        await session.commit()
        try:
            from app.events.render_bridge import emit_render_terminal, publish_render_status

            await publish_render_status(
                workspace_id=render.workspace_id,
                render_id=render.id,
                status="failed",
                error_message=str(exc)[:300],
                video_project_id=render.video_project_id,
            )
            await emit_render_terminal(
                session,
                workspace_id=render.workspace_id,
                render_id=render.id,
                video_project_id=render.video_project_id,
                ok=False,
                actor_id=actor_id,
                error=str(exc)[:300],
            )
            await session.commit()
        except Exception:
            logger.warning("failed-render hub publish failed render_id=%s", render.id, exc_info=True)
        await _notify_render_email(
            session,
            render,
            settings,
            ok=False,
            actor_id=actor_id,
            error=str(exc)[:300],
        )
        raise

    render.status = "complete"
    render.output_url = output_url
    render.error_message = None
    render.render_metadata = {
        **dict(render.render_metadata or {}),
        "renderer": "ffmpeg_concat",
        "output_url": output_url,
        **sidecar_urls,
        **sync_metadata,
        "captions_burned_in": captions_burned_in,
    }
    await session.execute(delete(CaptionTrack).where(CaptionTrack.video_render_id == render.id))
    if sidecar_urls.get("captions_vtt_url"):
        session.add(
            CaptionTrack(
                workspace_id=render.workspace_id,
                video_render_id=render.id,
                format="vtt",
                language="en",
                url=sidecar_urls["captions_vtt_url"],
                burned_in=False,
                track_metadata={"source": "render_pipeline"},
            )
        )
    if sidecar_urls.get("captions_srt_url"):
        session.add(
            CaptionTrack(
                workspace_id=render.workspace_id,
                video_render_id=render.id,
                format="srt",
                language="en",
                url=sidecar_urls["captions_srt_url"],
                burned_in=False,
                track_metadata={"source": "render_pipeline"},
            )
        )
    if captions_burned_in:
        session.add(
            CaptionTrack(
                workspace_id=render.workspace_id,
                video_render_id=render.id,
                format="burn_in",
                language="en",
                url=output_url,
                burned_in=True,
                track_metadata={"source": "render_pipeline"},
            )
        )
    render.project.status = "complete"
    if job is not None:
        job.status = "complete"
        job.error_message = None
    session.add(
        AuditEvent(
            workspace_id=render.workspace_id,
            actor_id=actor_id,
            action="video_render.complete",
            details={"render_id": str(render.id), "output_url": output_url},
        )
    )
    await session.commit()
    try:
        from app.events.render_bridge import emit_render_terminal, publish_render_status

        await publish_render_status(
            workspace_id=render.workspace_id,
            render_id=render.id,
            status="complete",
            output_url=output_url,
            video_project_id=render.video_project_id,
        )
        await emit_render_terminal(
            session,
            workspace_id=render.workspace_id,
            render_id=render.id,
            video_project_id=render.video_project_id,
            ok=True,
            actor_id=actor_id,
        )
        await session.commit()
    except Exception:
        logger.warning("post-render hub publish failed render_id=%s", render.id, exc_info=True)
    await _notify_render_email(session, render, settings, ok=True, actor_id=actor_id)
    return render


async def _notify_render_email(
    session: AsyncSession,
    render: VideoRender,
    settings: Settings,
    *,
    ok: bool,
    actor_id: UUID | None,
    error: str | None = None,
) -> None:
    try:
        from app import email_templates as templates
        from app.email_notify import emails_for_user_ids, safe_send_email
        from app.models import User

        project = render.project
        title = project.title if project is not None else "Video project"
        project_id = project.id if project is not None else render.video_project_id
        studio_url = f"{settings.app_base_url.rstrip('/')}/clips"
        recipients = await emails_for_user_ids(
            session,
            [actor_id, getattr(project, "created_by_id", None) if project is not None else None],
        )
        if not recipients and project is not None and project.created_by_id:
            user = await session.get(User, project.created_by_id)
            if user and user.email and not getattr(user, "is_disabled", False):
                recipients = [user.email]
        if ok:
            subject, body = templates.render_complete(project_title=title, studio_url=studio_url)
        else:
            subject, body = templates.render_failed(project_title=title, error=error, studio_url=studio_url)
        await safe_send_email(subject, body, recipients, settings)
    except Exception:
        logger.warning("render email notify failed render_id=%s ok=%s", render.id, ok, exc_info=True)


async def next_queued_render(session: AsyncSession) -> VideoRender | None:
    """Claim one queued render with SKIP LOCKED so multi-worker races cannot double-process."""
    result = await session.execute(
        select(VideoRender)
        .options(selectinload(VideoRender.jobs))
        .where(VideoRender.status == "queued")
        .order_by(VideoRender.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    render = result.scalar_one_or_none()
    if render is None:
        return None
    render.status = "processing"
    job = sorted(render.jobs, key=lambda item: item.created_at, reverse=True)[0] if render.jobs else None
    if job is not None and job.status == "queued":
        job.status = "processing"
    await session.commit()
    return render
