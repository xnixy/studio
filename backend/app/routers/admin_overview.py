"""admin_overview platform admin routes."""
from __future__ import annotations

from app.routers._admin_shared import *  # noqa: F403
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/overview", response_model=AdminOverviewDto)
async def admin_overview(
    request: Request,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AdminOverviewDto:
    users = int(await session.scalar(select(func.count()).select_from(User)) or 0)
    admins = int(await session.scalar(select(func.count()).select_from(User).where(User.role == "admin")) or 0)
    disabled_users = int(await session.scalar(select(func.count()).select_from(User).where(User.is_disabled.is_(True))) or 0)
    workspaces = int(await session.scalar(select(func.count()).select_from(Workspace)) or 0)
    contacts_total = int(await session.scalar(select(func.count()).select_from(ContactMessage)) or 0)
    contacts_open = int(
        await session.scalar(select(func.count()).select_from(ContactMessage).where(ContactMessage.resolved_at.is_(None))) or 0
    )
    jobs_queued = int(await session.scalar(select(func.count()).select_from(BackgroundJob).where(BackgroundJob.status == "queued")) or 0)
    jobs_running = int(await session.scalar(select(func.count()).select_from(BackgroundJob).where(BackgroundJob.status == "running")) or 0)
    jobs_failed = int(await session.scalar(select(func.count()).select_from(BackgroundJob).where(BackgroundJob.status == "failed")) or 0)
    renders_queued = int(await session.scalar(select(func.count()).select_from(VideoRender).where(VideoRender.status == "queued")) or 0)
    renders_running = int(
        await session.scalar(
            select(func.count()).select_from(VideoRender).where(VideoRender.status.in_(("processing", "rendering", "uploading")))
        )
        or 0
    )

    plan_rows = (await session.execute(select(Subscription.plan, func.count()).group_by(Subscription.plan))).all()
    subscriptions_by_plan = {str(plan): int(count) for plan, count in plan_rows}

    maintenance = await session.get(MaintenanceSetting, 1)
    limiter = request.app.state.rate_limiter
    redis_healthy = False
    if limiter.redis is not None:
        try:
            await limiter.redis.ping()
            redis_healthy = True
        except Exception:
            redis_healthy = False

    return AdminOverviewDto(
        users=users,
        admins=admins,
        disabled_users=disabled_users,
        workspaces=workspaces,
        contacts_open=contacts_open,
        contacts_total=contacts_total,
        jobs_queued=jobs_queued,
        jobs_running=jobs_running,
        jobs_failed=jobs_failed,
        renders_queued=renders_queued,
        renders_running=renders_running,
        subscriptions_by_plan=subscriptions_by_plan,
        maintenance_enabled=bool(maintenance.enabled) if maintenance else False,
        stripe_configured=bool(settings.stripe_secret_key and settings.stripe_price_ids),
        redis_healthy=redis_healthy,
        ffmpeg_available=bool(ffmpeg_path()),
        r2_enabled=settings.r2_enabled,
        xai_configured=bool(settings.xai_api_key),
    )


