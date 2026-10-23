"""jobs API routes."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.job_queue import cancel_job, enqueue_kwargs
from app.jobs.base import read_permission_for, write_permission_for
from app.models import AuditEvent, BackgroundJob, User
from app.routers._agency_shared import log_audit, map_job
from app.schemas import BackgroundJobDto, BackgroundJobEnqueueRequest, BackgroundJobStatsDto
from app.workspace_access import require_permission

router = APIRouter(tags=["jobs"])


@router.get("/jobs", response_model=list[BackgroundJobDto])
async def list_jobs(
    workspace_id: UUID,
    job_type: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[BackgroundJobDto]:
    await require_permission(session, workspace_id, user, "projects.read")
    limit = max(1, min(limit, 200))
    query = (
        select(BackgroundJob)
        .where(BackgroundJob.workspace_id == workspace_id)
        .order_by(BackgroundJob.created_at.desc())
        .limit(limit)
    )
    if job_type:
        query = query.where(BackgroundJob.job_type == job_type)
    if status_filter:
        query = query.where(BackgroundJob.status == status_filter)
    jobs = (await session.scalars(query)).all()
    visible: list[BackgroundJobDto] = []
    for job in jobs:
        try:
            await require_permission(session, workspace_id, user, read_permission_for(job.job_type))
        except HTTPException:
            continue
        visible.append(map_job(job))
    return visible


@router.get("/jobs/stats", response_model=BackgroundJobStatsDto)
async def job_stats(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BackgroundJobStatsDto:
    await require_permission(session, workspace_id, user, "audit.read")
    from sqlalchemy import func

    rows = (
        await session.execute(
            select(BackgroundJob.status, func.count())
            .where(BackgroundJob.workspace_id == workspace_id)
            .group_by(BackgroundJob.status)
        )
    ).all()
    counts = {status_name: int(count) for status_name, count in rows}
    return BackgroundJobStatsDto(
        workspace_id=workspace_id,
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        waiting_for_provider=counts.get("waiting_for_provider", 0),
        completed=counts.get("completed", 0),
        failed=counts.get("failed", 0),
        canceled=counts.get("canceled", 0),
    )


@router.get("/jobs/{job_id}", response_model=BackgroundJobDto)
async def get_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BackgroundJobDto:
    job = await session.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    await require_permission(session, job.workspace_id, user, read_permission_for(job.job_type))
    return map_job(job)


@router.post("/jobs", response_model=BackgroundJobDto, status_code=status.HTTP_201_CREATED)
async def enqueue_job(
    payload: BackgroundJobEnqueueRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BackgroundJobDto:
    """Enqueue a background job for the workspace (echo and domain job types)."""
    await require_permission(session, payload.workspace_id, user, write_permission_for(payload.job_type))
    if payload.idempotency_key:
        existing = await session.scalar(
            select(BackgroundJob).where(
                BackgroundJob.workspace_id == payload.workspace_id,
                BackgroundJob.idempotency_key == payload.idempotency_key,
            )
        )
        if existing is not None:
            return map_job(existing)

    job = BackgroundJob(
        **enqueue_kwargs(
            workspace_id=payload.workspace_id,
            job_type=payload.job_type,
            payload=payload.payload,
            created_by_id=user.id,
            priority=payload.priority,
            idempotency_key=payload.idempotency_key,
        )
    )
    session.add(job)
    await log_audit(
        session,
        payload.workspace_id,
        user.id,
        "job.enqueued",
        {"job_type": payload.job_type, "job_id": str(job.id)},
    )
    await session.commit()
    await session.refresh(job)
    return map_job(job)


@router.post("/jobs/{job_id}/cancel", response_model=BackgroundJobDto)
async def cancel_background_job(
    job_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> BackgroundJobDto:
    job = await session.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    await require_permission(session, job.workspace_id, user, write_permission_for(job.job_type))
    if job.status in ("completed", "failed", "canceled"):
        return map_job(job)
    job = await cancel_job(session, job)
    session.add(
        AuditEvent(
            workspace_id=job.workspace_id,
            actor_id=user.id,
            action="job.cancel_requested",
            details={"job_id": str(job.id), "status": job.status},
        )
    )
    await session.commit()
    await session.refresh(job)
    return map_job(job)
