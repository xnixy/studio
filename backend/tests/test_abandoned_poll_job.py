"""A stranded poll job must not keep the HTTP poll from taking over.

The worker owns provider polling, so the client poll steps aside when a job is
live. When the worker dies, the tick budget and the stuck-asset sweep die with
it — so "live" has to mean live, or the clip spins forever and never refunds.
"""
from datetime import timedelta

from app.job_queue import ABANDONED_JOB_GRACE_SECONDS, job_is_abandoned
from app.jobs.base import utcnow


class _Job:
    def __init__(self, status: str, *, scheduled_for=None, lease_expires_at=None) -> None:
        self.status = status
        self.scheduled_for = scheduled_for
        self.lease_expires_at = lease_expires_at


def test_deferred_tick_waiting_its_turn_is_live() -> None:
    # Poll ticks requeue with scheduled_for up to 20s out; a worker claims within one interval.
    job = _Job("queued", scheduled_for=utcnow() + timedelta(seconds=20))
    assert job_is_abandoned(job) is False


def test_recently_due_tick_is_live() -> None:
    # Due a moment ago just means the claim loop has not come around yet.
    job = _Job("queued", scheduled_for=utcnow() - timedelta(seconds=10))
    assert job_is_abandoned(job) is False


def test_queued_job_long_past_due_is_abandoned() -> None:
    job = _Job("queued", scheduled_for=utcnow() - timedelta(seconds=ABANDONED_JOB_GRACE_SECONDS + 60))
    assert job_is_abandoned(job) is True


def test_running_job_inside_its_lease_is_live() -> None:
    job = _Job("running", lease_expires_at=utcnow() + timedelta(minutes=4))
    assert job_is_abandoned(job) is False


def test_running_job_with_expired_lease_is_abandoned() -> None:
    # The holder died mid-run; requeue_expired_leases needs a live worker to reap it.
    job = _Job("running", lease_expires_at=utcnow() - timedelta(minutes=1))
    assert job_is_abandoned(job) is True


def test_waiting_for_provider_with_expired_lease_is_abandoned() -> None:
    job = _Job("waiting_for_provider", lease_expires_at=utcnow() - timedelta(minutes=1))
    assert job_is_abandoned(job) is True


def test_terminal_job_is_not_abandoned() -> None:
    # Terminal rows are not candidates either way; the route filters them out first.
    job = _Job("completed", scheduled_for=utcnow() - timedelta(days=1))
    assert job_is_abandoned(job) is False


def test_missing_timestamps_are_treated_as_live() -> None:
    # Unknown state must not license a second poller onto the same row.
    assert job_is_abandoned(_Job("queued", scheduled_for=None)) is False
    assert job_is_abandoned(_Job("running", lease_expires_at=None)) is False
