"""Shared helpers for jobs + audit (agency client graph removed)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent, BackgroundJob
from app.schemas import BackgroundJobDto


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def log_audit(
    session: AsyncSession, workspace_id: UUID, actor_id: UUID | None, action: str, details: dict[str, object]
) -> None:
    """Record an audit event."""
    session.add(AuditEvent(workspace_id=workspace_id, actor_id=actor_id, action=action, details=details))


# Back-compat alias
_log = log_audit


def map_job(job: BackgroundJob) -> BackgroundJobDto:
    return BackgroundJobDto(
        id=job.id,
        workspace_id=job.workspace_id,
        job_type=job.job_type,
        status=job.status,  # type: ignore[arg-type]
        priority=job.priority,
        payload=dict(job.payload or {}),
        result=dict(job.result or {}),
        error_message=job.error_message,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        scheduled_for=job.scheduled_for,
        lease_expires_at=job.lease_expires_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
        created_by_id=job.created_by_id,
        idempotency_key=job.idempotency_key,
        usage_event_id=job.usage_event_id,
        cancel_requested=job.cancel_requested,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
