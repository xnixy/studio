"""Map domain job types / statuses to notification copy and deep links."""

from __future__ import annotations

from typing import Any
from uuid import UUID


JOB_TYPE_META: dict[str, dict[str, str]] = {
    "echo": {
        "completed_type": "job.completed",
        "failed_type": "job.failed",
        "completed_title": "Background task finished",
        "failed_title": "Background task failed",
        "href": "/clips",
    },
}

# These jobs already emit a user-facing asset event (clip ready / failed).
# A second push with generic job copy is the duplicate banner on iOS.
_SILENT_JOB_TYPES = frozenset({"webhook.deliver", "video.asset.poll"})


def job_notification_spec(
    job_type: str,
    status: str,
    *,
    job_id: UUID,
    error_message: str | None = None,
    result: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if status not in {"completed", "failed", "canceled"}:
        return None
    if job_type in _SILENT_JOB_TYPES:
        return None

    meta = JOB_TYPE_META.get(job_type)
    if status == "completed":
        event_type = (meta or {}).get("completed_type") or "job.completed"
        title = (meta or {}).get("completed_title") or "Background task finished"
        body = "You're good to open it and keep going."
    elif status == "failed":
        event_type = (meta or {}).get("failed_type") or "job.failed"
        title = (meta or {}).get("failed_title") or "Background task failed"
        body = (error_message or "Something went wrong. Try again in a bit.")[:500]
    else:
        event_type = "job.canceled"
        title = "Background task canceled"
        body = error_message or "The task was canceled."

    href = (meta or {}).get("href") or "/clips"
    return {
        "type": event_type,
        "title": title,
        "body": body,
        "href": href,
        "entity_kind": "background_job",
        "entity_id": job_id,
        "payload": {
            "job_type": job_type,
            "status": status,
            "result": result or {},
        },
        "dedupe_key": f"job:{job_id}:{status}",
        "recipient_mode": "workspace_members",
        "persist": True,
        "live": True,
        "toast": True,
    }
