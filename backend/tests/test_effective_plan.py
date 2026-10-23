"""Unit tests for subscription period / status → effective plan."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.workspace_access import effective_plan_name


def _sub(**kwargs):
    base = {
        "plan": "starter",
        "status": "active",
        "current_period_end": datetime.now(timezone.utc) + timedelta(days=10),
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_active_paid_within_period() -> None:
    assert effective_plan_name(_sub()) == "starter"  # type: ignore[arg-type]


def test_period_ended_falls_to_free() -> None:
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    assert effective_plan_name(_sub(current_period_end=past)) == "free"  # type: ignore[arg-type]


def test_canceled_still_active_until_period_end() -> None:
    future = datetime.now(timezone.utc) + timedelta(days=5)
    assert (
        effective_plan_name(_sub(status="canceled", current_period_end=future))  # type: ignore[arg-type]
        == "starter"
    )


def test_canceled_after_period_is_free() -> None:
    past = datetime.now(timezone.utc) - timedelta(days=1)
    assert (
        effective_plan_name(_sub(status="canceled", current_period_end=past))  # type: ignore[arg-type]
        == "free"
    )


def test_expired_status_is_free() -> None:
    assert effective_plan_name(_sub(status="expired")) == "free"  # type: ignore[arg-type]


def test_free_plan_unchanged() -> None:
    assert effective_plan_name(_sub(plan="free", status="active")) == "free"  # type: ignore[arg-type]


def test_naive_period_end_treated_as_utc() -> None:
    past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=2)
    assert effective_plan_name(_sub(current_period_end=past)) == "free"  # type: ignore[arg-type]
