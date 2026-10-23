"""Idempotent reservation release for Play generate paths."""
from __future__ import annotations

from app.workspace_access import finish_usage


async def release_if_unsettled(session, reservation_type, reservation_id) -> None:
    """Release a reservation only while it is still reserved.

    finish_usage overwrites status unconditionally, so a second release could
    flip an already consumed reservation back to released and hand out a free
    clip. Checking the current status makes the call safe to repeat.
    """
    try:
        stored = await session.get(reservation_type, reservation_id)
        if stored is not None and stored.status == "reserved":
            await finish_usage(session, stored, consumed=False)
    except Exception:
        pass


async def release_if_reserved(session, reservation) -> None:
    """Same as release_if_unsettled when the caller still has the row object."""
    if reservation is None:
        return
    await release_if_unsettled(session, type(reservation), reservation.id)
