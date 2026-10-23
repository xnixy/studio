"""No-op / smoke-test job handler."""

from __future__ import annotations

from typing import Any

from app.jobs.base import JobContext


class EchoHandler:
    job_type = "echo"

    async def run(self, ctx: JobContext) -> dict[str, Any]:
        if ctx.job.cancel_requested:
            raise JobCanceled()
        message = str((ctx.job.payload or {}).get("message") or "ok")
        return {"echo": message, "attempts": ctx.job.attempts}


class JobCanceled(Exception):
    """Handler cooperative cancel."""
