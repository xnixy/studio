"""admin_jobs platform admin routes."""
from __future__ import annotations

from app.routers._admin_shared import *  # noqa: F403
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/jobs/stats", response_model=AdminJobStatsDto)
async def job_stats(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminJobStatsDto:
    rows = (await session.execute(select(BackgroundJob.status, func.count()).group_by(BackgroundJob.status))).all()
    counts = {str(status_value): int(count) for status_value, count in rows}
    return AdminJobStatsDto(
        queued=counts.get("queued", 0),
        running=counts.get("running", 0),
        failed=counts.get("failed", 0),
        completed=counts.get("completed", 0),
        canceled=counts.get("canceled", 0),
    )


@router.get("/jobs", response_model=list[AdminJobDto])
async def list_jobs(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[AdminJobDto]:
    stmt = select(BackgroundJob).order_by(BackgroundJob.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(BackgroundJob.status == status_filter)
    jobs = (await session.scalars(stmt)).all()
    return [
        AdminJobDto(
            id=job.id,
            workspace_id=job.workspace_id,
            job_type=job.job_type,
            status=job.status,
            attempts=int(job.attempts or 0),
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
        )
        for job in jobs
    ]


@router.post("/jobs/{job_id}/cancel", response_model=AdminJobDto)
async def cancel_admin_job(
    job_id: UUID,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminJobDto:
    job = await session.get(BackgroundJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status not in ("completed", "failed", "canceled"):
        job = await cancel_job(session, job)
    return AdminJobDto(
        id=job.id,
        workspace_id=job.workspace_id,
        job_type=job.job_type,
        status=job.status,
        attempts=int(job.attempts or 0),
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


