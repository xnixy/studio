"""Job type → handler registry."""

from __future__ import annotations

from app.jobs.base import JobHandler
from app.jobs.echo import EchoHandler
from app.jobs.video_asset_poll import VideoAssetPollHandler

_HANDLERS: dict[str, JobHandler] = {}
_REGISTERED = False


def register(handler: JobHandler) -> None:
    _HANDLERS[handler.job_type] = handler


def get_handler(job_type: str) -> JobHandler | None:
    register_builtin_handlers()
    return _HANDLERS.get(job_type)


def register_builtin_handlers() -> None:
    global _REGISTERED
    if _REGISTERED:
        return
    register(EchoHandler())
    register(VideoAssetPollHandler())
    _REGISTERED = True
