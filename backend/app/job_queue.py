"""BackgroundJob claim, reaper, and terminal state helpers.

Claim uses FOR UPDATE SKIP LOCKED — this is intentional new behavior,
not a reuse of next_queued_render (which has no row locking today).
"""

from __future__ import annotations

import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.base import (
    DEFAULT_MAX_CONCURRENT,
    MAX_CLAIM_TRIES,
    JobContext,
    JobDeferred,
    backoff_seconds,
    lease_for,
    utcnow,
)
from app.jobs.echo import JobCanceled
from app.jobs.registry import get_handler, register_builtin_handlers
from app.models import BackgroundJob, UsageEvent
from app.workspace_access import finish_usage

logger = logging.getLogger(__name__)


# A healthy worker re-claims a deferred job within its delay (<=20s for poll ticks)
# plus one poll interval. Well past that means nothing is working the row: the
# worker is down, crash-looping, or was redeployed mid-flight.
ABANDONED_JOB_GRACE_SECONDS = 120


def job_is_abandoned(job: BackgroundJob, *, grace_seconds: int = ABANDONED_JOB_GRACE_SECONDS) -> bool:
    """True when a non-terminal job has no live worker behind it.

    Callers that skip work because "a job owns this" need to distinguish a job
    that is actually in flight from one stranded by a dead worker — otherwise a
    worker outage reads to the client as work that never finishes.
    """
    if job.status not in {"queued", "running", "waiting_for_provider"}:
        return False
    now = utcnow()
    if job.status == "queued":
        # Deferred ticks land here with scheduled_for in the near future; a claim
        # follows within one poll interval of that time.
        scheduled_for = job.scheduled_for
        if scheduled_for is None:
            return False
        return scheduled_for < now - timedelta(seconds=grace_seconds)
    # Claimed states carry a lease. An expired one means the holder died mid-run;
    # requeue_expired_leases would reap it if a worker were alive to run it.
    lease_expires_at = job.lease_expires_at
    if lease_expires_at is None:
        return False
    return lease_expires_at < now


async def count_running(session: AsyncSession, workspace_id: UUID) -> int:
    total = await session.scalar(
        select(func.count())
        .select_from(BackgroundJob)
        .where(BackgroundJob.workspace_id == workspace_id, BackgroundJob.status == "running")
    )
    return int(total or 0)


async def claim_next_job(
    session: AsyncSession,
    *,
    max_concurrent: int = DEFAULT_MAX_CONCURRENT,
    max_tries: int = MAX_CLAIM_TRIES,
) -> BackgroundJob | None:
    """Claim one queued job with SKIP LOCKED, deferring saturated workspaces."""
    now = utcnow()
    for _ in range(max_tries):
        result = await session.execute(
            select(BackgroundJob)
            .where(
                BackgroundJob.status == "queued",
                BackgroundJob.scheduled_for <= now,
                BackgroundJob.cancel_requested.is_(False),
            )
            .order_by(BackgroundJob.priority.asc(), BackgroundJob.created_at.asc())
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        candidate = result.scalar_one_or_none()
        if candidate is None:
            return None

        in_flight = await count_running(session, candidate.workspace_id)
        if in_flight >= max_concurrent:
            # Defer slightly so other workspaces can proceed (no head-of-line block).
            candidate.scheduled_for = now + timedelta(seconds=2)
            await session.commit()
            continue

        candidate.status = "running"
        candidate.attempts = int(candidate.attempts or 0) + 1
        candidate.started_at = now
        candidate.lease_expires_at = now + lease_for(candidate.job_type)
        candidate.error_message = None
        await session.commit()
        await session.refresh(candidate)
        return candidate

    return None


async def requeue_expired_leases(session: AsyncSession) -> int:
    """Reap stuck running/waiting jobs whose lease expired."""
    now = utcnow()
    jobs = (
        await session.scalars(
            select(BackgroundJob)
            .where(
                BackgroundJob.status.in_(("running", "waiting_for_provider")),
                BackgroundJob.lease_expires_at.is_not(None),
                BackgroundJob.lease_expires_at < now,
            )
            .with_for_update(skip_locked=True)
            .limit(50)
        )
    ).all()
    reaped = 0
    for job in jobs:
        if job.cancel_requested:
            await mark_terminal(session, job, status="canceled", error="Canceled after lease expiry", commit=False)
            reaped += 1
            continue
        if int(job.attempts or 0) >= int(job.max_attempts or 3):
            await mark_terminal(
                session,
                job,
                status="failed",
                error="Lease expired and max attempts reached",
                commit=False,
            )
            reaped += 1
            continue
        job.status = "queued"
        job.lease_expires_at = None
        job.started_at = None
        job.scheduled_for = now + timedelta(seconds=backoff_seconds(int(job.attempts or 1)))
        job.error_message = "Lease expired; requeued"
        reaped += 1
    if reaped:
        await session.commit()
    return reaped


async def mark_terminal(
    session: AsyncSession,
    job: BackgroundJob,
    *,
    status: str,
    result: dict | None = None,
    error: str | None = None,
    commit: bool = True,
) -> None:
    now = utcnow()
    job.status = status
    job.finished_at = now
    job.lease_expires_at = None
    if result is not None:
        job.result = result
    if error is not None:
        job.error_message = error

    if job.usage_event_id is not None:
        event = await session.get(UsageEvent, job.usage_event_id)
        if event is not None and event.status == "reserved":
            await finish_usage(session, event, consumed=(status == "completed"), commit=False)

    if commit:
        await session.commit()

    # In-app + live notifications for terminal states (best-effort; never raises).
    if status in {"completed", "failed", "canceled"} and job.job_type != "webhook.deliver":
        try:
            from app.events.emit import emit_job_terminal

            await emit_job_terminal(
                session,
                workspace_id=job.workspace_id,
                job_id=job.id,
                job_type=job.job_type,
                status=status,
                created_by_id=job.created_by_id,
                error_message=job.error_message,
                result=dict(job.result or {}),
                # Own commit when parent already committed; else join parent transaction.
                commit=commit,
            )
        except Exception:
            logger.exception("notification emit failed for job %s", job.id)


async def fail_or_retry(session: AsyncSession, job: BackgroundJob, error: str) -> None:
    attempts = int(job.attempts or 0)
    max_attempts = int(job.max_attempts or 3)
    if attempts >= max_attempts:
        await mark_terminal(session, job, status="failed", error=error)
        return
    job.status = "queued"
    job.lease_expires_at = None
    job.started_at = None
    job.scheduled_for = utcnow() + timedelta(seconds=backoff_seconds(attempts))
    job.error_message = error
    await session.commit()


async def _emit_job_webhook(
    session: AsyncSession,
    job: BackgroundJob,
    *,
    status: str,
    result: dict,
) -> None:
    """Webhook fan-out removed with integrations surface; kept as no-op hook."""
    _ = (session, job, status, result)
    return


async def process_job(session: AsyncSession, job: BackgroundJob) -> None:
    """Run handler for an already-claimed job. Handler runs outside claim tx."""
    register_builtin_handlers()

    # Cooperative cancel before work
    if job.cancel_requested:
        await mark_terminal(session, job, status="canceled", error="Canceled before start")
        return

    handler = get_handler(job.job_type)
    if handler is None:
        await mark_terminal(session, job, status="failed", error=f"No handler for job_type={job.job_type}")
        return

    # Refresh cancel flag mid-flight is cooperative; re-load job
    try:
        result = await handler.run(JobContext(session=session, job=job, workspace_id=job.workspace_id))
        # Re-check cancel after work
        await session.refresh(job)
        if job.cancel_requested:
            await mark_terminal(session, job, status="canceled", error="Canceled after work", result=result)
            return
        await mark_terminal(session, job, status="completed", result=result or {})
        await _emit_job_webhook(session, job, status="completed", result=result or {})
    except JobDeferred as defer:
        await session.refresh(job)
        if job.cancel_requested:
            await mark_terminal(session, job, status="canceled", error="Canceled while deferred")
            return
        # Soft requeue: do not burn attempt budget for provider wait ticks.
        job.status = "queued"
        job.lease_expires_at = None
        job.started_at = None
        job.attempts = max(0, int(job.attempts or 1) - 1)
        job.scheduled_for = utcnow() + timedelta(seconds=defer.delay_seconds)
        job.error_message = None
        payload = dict(job.payload or {})
        payload["poll_ticks"] = int(payload.get("poll_ticks") or 0) + 1
        if defer.result:
            payload["last_defer"] = defer.result
        job.payload = payload
        if defer.result:
            job.result = defer.result
        await session.commit()
    except JobCanceled:
        await mark_terminal(session, job, status="canceled", error="Canceled by handler")
    except Exception as exc:
        logger.exception("Job %s (%s) failed", job.id, job.job_type)
        await session.rollback()
        # Reload job after rollback
        stored = await session.get(BackgroundJob, job.id)
        if stored is None:
            return
        prev_attempts = int(stored.attempts or 0)
        max_attempts = int(stored.max_attempts or 3)
        await fail_or_retry(session, stored, str(exc)[:2000])
        # Fan out only on terminal failure (not intermediate requeue)
        if prev_attempts >= max_attempts:
            reloaded = await session.get(BackgroundJob, job.id)
            if reloaded is not None and reloaded.status == "failed":
                await _emit_job_webhook(session, reloaded, status="failed", result={})


async def cancel_job(session: AsyncSession, job: BackgroundJob) -> BackgroundJob:
    """Request cancel; terminal immediately if still queued."""
    job.cancel_requested = True
    if job.status == "queued":
        await mark_terminal(session, job, status="canceled", error="Canceled while queued")
    else:
        await session.commit()
        await session.refresh(job)
    return job


def enqueue_kwargs(
    *,
    workspace_id: UUID,
    job_type: str,
    payload: dict | None = None,
    created_by_id: UUID | None = None,
    priority: int = 100,
    max_attempts: int = 3,
    idempotency_key: str | None = None,
    usage_event_id: UUID | None = None,
    priority_boost: bool = False,
) -> dict:
    """Build constructor kwargs for BackgroundJob."""
    if priority_boost:
        priority = min(priority, 50)
    return {
        "workspace_id": workspace_id,
        "job_type": job_type,
        "status": "queued",
        "priority": priority,
        "payload": payload or {},
        "result": {},
        "attempts": 0,
        "max_attempts": max_attempts,
        "scheduled_for": utcnow(),
        "created_by_id": created_by_id,
        "idempotency_key": idempotency_key,
        "usage_event_id": usage_event_id,
        "cancel_requested": False,
    }
