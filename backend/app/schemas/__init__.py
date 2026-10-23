"""Pydantic request/response schemas, split by domain.

Import from the package hub so call sites stay stable:
  `from app.schemas import UserDto, VideoProjectDto`
"""
from __future__ import annotations

from app.schemas.common import *  # noqa: F403
from app.schemas.auth import *  # noqa: F403
from app.schemas.system import *  # noqa: F403
from app.schemas.admin import *  # noqa: F403
from app.schemas.workspace import *  # noqa: F403
from app.schemas.billing import *  # noqa: F403
from app.schemas.video import *  # noqa: F403
from app.schemas.agency import *  # noqa: F403  # ShareLink public DTOs
from app.schemas.jobs import *  # noqa: F403
from app.schemas.notifications import *  # noqa: F403
from app.schemas.play import *  # noqa: F403
from app.schemas.voices import *  # noqa: F403

_exported = {n for n in globals() if not n.startswith("_")}
__all__ = sorted(_exported)
