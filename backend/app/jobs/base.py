"""Shared job handler types and lease helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BackgroundJob

DEFAULT_LEASE = timedelta(minutes=15)
DEFAULT_MAX_CONCURRENT = 2
MAX_CLAIM_TRIES = 16

LEASE_BY_JOB_TYPE: dict[str, timedelta] = {
    "echo": timedelta(minutes=5),
    # One provider status tick + optional download; reschedule if still processing.
    "video.asset.poll": timedelta(minutes=5),
}

JOB_TYPE_READ_PERMISSION: dict[str, str] = {
    "echo": "projects.read",
    "video.asset.poll": "projects.read",
}

JOB_TYPE_WRITE_PERMISSION: dict[str, str] = {
    "echo": "projects.write",
    "video.asset.poll": "projects.write",
}


class JobDeferred(Exception):
    """Handler asks the worker to requeue without treating as failure."""

    def __init__(self, delay_seconds: int = 8, *, result: dict | None = None):
        super().__init__(f"deferred {delay_seconds}s")
        self.delay_seconds = max(2, int(delay_seconds))
        self.result = result or {}



def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def lease_for(job_type: str) -> timedelta:
    return LEASE_BY_JOB_TYPE.get(job_type, DEFAULT_LEASE)


def backoff_seconds(attempts: int) -> int:
    """Exponential backoff capped at 1 hour. attempts is post-claim count."""
    return min(3600, 30 * (2 ** max(0, attempts - 1)))


def read_permission_for(job_type: str) -> str:
    return JOB_TYPE_READ_PERMISSION.get(job_type, "projects.read")


def write_permission_for(job_type: str) -> str:
    return JOB_TYPE_WRITE_PERMISSION.get(job_type, "projects.write")


@dataclass
class JobContext:
    session: AsyncSession
    job: BackgroundJob
    workspace_id: UUID


class JobHandler(Protocol):
    job_type: str

    async def run(self, ctx: JobContext) -> dict[str, Any]:
        """Execute work. Return result dict on success. Raise on failure."""
        ...
