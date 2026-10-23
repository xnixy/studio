"""Reservations must not survive a failed start, or flip after a good one."""
import asyncio

from app.play_billing import release_if_unsettled as _release_if_unsettled


class _Event:
    def __init__(self, status: str) -> None:
        self.status = status


class _Session:
    def __init__(self, event: _Event | None) -> None:
        self.event = event
        self.committed = False

    async def get(self, _type: object, _id: object) -> _Event | None:
        return self.event

    async def commit(self) -> None:
        self.committed = True


def test_reserved_row_is_released() -> None:
    event = _Event("reserved")
    session = _Session(event)
    asyncio.run(_release_if_unsettled(session, _Event, "id"))
    assert event.status == "released"


def test_consumed_row_is_left_alone() -> None:
    # A late failure after the clip started must not hand back a paid clip.
    event = _Event("consumed")
    session = _Session(event)
    asyncio.run(_release_if_unsettled(session, _Event, "id"))
    assert event.status == "consumed"


def test_repeat_release_is_harmless() -> None:
    event = _Event("reserved")
    session = _Session(event)
    asyncio.run(_release_if_unsettled(session, _Event, "id"))
    asyncio.run(_release_if_unsettled(session, _Event, "id"))
    assert event.status == "released"


def test_missing_row_does_not_raise() -> None:
    asyncio.run(_release_if_unsettled(_Session(None), _Event, "id"))


def test_reaper_cannot_outrun_a_live_poll_job() -> None:
    """The stuck-asset sweep must never fail a clip still inside its poll budget.

    Poll ticks back off from 8s to 20s over MAX_POLL_TICKS, and each tick writes
    the asset, refreshing updated_at. The reaper only looks at rows untouched
    past its ceiling, so the ceiling has to sit well beyond the whole budget.
    """
    from app.jobs.video_asset_poll import BASE_DELAY_SECONDS, MAX_DELAY_SECONDS, MAX_POLL_TICKS
    from app.video_asset_poll import STUCK_ASSET_MAX_AGE_SECONDS

    budget = sum(
        min(MAX_DELAY_SECONDS, BASE_DELAY_SECONDS + tick // 5) for tick in range(MAX_POLL_TICKS)
    )
    assert STUCK_ASSET_MAX_AGE_SECONDS > budget * 1.5
