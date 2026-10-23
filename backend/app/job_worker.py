"""Process BackgroundJob queue.

Usage:
  python -m app.job_worker --poll-seconds 5
  python -m app.job_worker --once
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import time

from app.database import SessionLocal
from app.job_queue import claim_next_job, process_job, requeue_expired_leases
from app.jobs.registry import register_builtin_handlers
from app.routers.auth_session import purge_dead_refresh_tokens
from app.video_asset_poll import fail_stuck_processing_assets

# Housekeeping, not queue work: once an hour is plenty.
TOKEN_PURGE_INTERVAL_SECONDS = 60 * 60
_last_token_purge = 0.0

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("job_worker")


async def process_once() -> bool:
    register_builtin_handlers()
    async with SessionLocal() as session:
        reaped = await requeue_expired_leases(session)
        if reaped:
            logger.info("Reaped %s expired lease(s)", reaped)

    async with SessionLocal() as session:
        stuck = await fail_stuck_processing_assets(session)
        if stuck:
            logger.info("Failed and refunded %s stuck asset(s)", stuck)

    global _last_token_purge
    now = time.monotonic()
    if now - _last_token_purge >= TOKEN_PURGE_INTERVAL_SECONDS:
        _last_token_purge = now
        async with SessionLocal() as session:
            purged = await purge_dead_refresh_tokens(session)
            if purged:
                logger.info("Purged %s dead refresh token(s)", purged)

    async with SessionLocal() as session:
        job = await claim_next_job(session)
        if job is None:
            logger.debug("No queued jobs.")
            return False
        logger.info("Processing job %s type=%s attempt=%s", job.id, job.job_type, job.attempts)
        try:
            # Fresh session for handler work so claim commit is isolated
            async with SessionLocal() as work_session:
                work_job = await work_session.get(type(job), job.id)
                if work_job is None:
                    return True
                await process_job(work_session, work_job)
                logger.info("Job %s finished status=%s", work_job.id, work_job.status)
        except Exception as exc:
            logger.exception("Job %s crashed: %s", job.id, exc)
        return True


async def run(limit: int, poll_seconds: float) -> None:
    processed = 0
    while limit <= 0 or processed < limit:
        did_work = await process_once()
        if did_work:
            processed += 1
            if limit == 1:
                break
            continue
        if poll_seconds <= 0:
            break
        await asyncio.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Process queued Studio background jobs.")
    parser.add_argument("--once", action="store_true", help="Process at most one job (after reaper).")
    parser.add_argument("--limit", type=int, default=0, help="Max jobs to process; 0 means until idle unless polling.")
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=0,
        help="Poll interval when idle; 0 exits when no work.",
    )
    args = parser.parse_args()
    limit = 1 if args.once else args.limit
    asyncio.run(run(limit=limit, poll_seconds=args.poll_seconds))


if __name__ == "__main__":
    main()
