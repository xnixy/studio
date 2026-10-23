"""Publish render status to the shared event hub (replaces pure in-memory hub)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.events.emit import emit_domain_event
from app.events.hub import event_hub


async def publish_render_status(
    *,
    workspace_id: UUID | str,
    render_id: UUID | str,
    status: str,
    output_url: str | None = None,
    error_message: str | None = None,
    video_project_id: UUID | str | None = None,
) -> None:
    """Live (and optional durable) render updates."""
    ws = str(workspace_id)
    event: dict[str, Any] = {
        "type": "render_status",
        "workspace_id": ws,
        "render_id": str(render_id),
        "status": status,
        "output_url": output_url,
        "error_message": error_message,
        "video_project_id": str(video_project_id) if video_project_id else None,
    }
    await event_hub.publish(event)


async def emit_render_terminal(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    render_id: UUID,
    video_project_id: UUID | None,
    ok: bool,
    actor_id: UUID | None,
    error: str | None = None,
) -> None:
    href = f"/studio/projects/{video_project_id}/video" if video_project_id else "/studio/overview"
    if ok:
        await emit_domain_event(
            session,
            type="render.completed",
            workspace_id=workspace_id,
            actor_user_id=actor_id,
            entity_kind="video_render",
            entity_id=render_id,
            title="Export ready",
            body="Your video export finished.",
            href=href,
            payload={"status": "complete"},
            recipient_mode="workspace_members",
            dedupe_key=f"render:{render_id}:complete",
            persist=True,
            live=True,
            toast=True,
            commit=False,
        )
    else:
        await emit_domain_event(
            session,
            type="render.failed",
            workspace_id=workspace_id,
            actor_user_id=actor_id,
            entity_kind="video_render",
            entity_id=render_id,
            title="Export failed",
            body=(error or "Something went wrong while exporting.")[:500],
            href=href,
            payload={"status": "failed", "error": error},
            recipient_mode="workspace_members",
            dedupe_key=f"render:{render_id}:failed",
            persist=True,
            live=True,
            toast=True,
            commit=False,
        )
