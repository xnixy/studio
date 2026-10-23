"""Unit tests for notification event catalog mapping."""

from uuid import uuid4

from app.events.catalog import job_notification_spec


def test_echo_completed_maps():
    job_id = uuid4()
    spec = job_notification_spec("echo", "completed", job_id=job_id)
    assert spec is not None
    assert spec["type"] == "job.completed"
    assert spec["persist"] is True
    assert spec["dedupe_key"] == f"job:{job_id}:completed"


def test_webhook_deliver_skipped():
    assert job_notification_spec("webhook.deliver", "completed", job_id=uuid4()) is None


def test_video_asset_poll_skipped():
    """Clip ready/failed already comes from emit_asset_terminal."""
    job_id = uuid4()
    assert job_notification_spec("video.asset.poll", "completed", job_id=job_id) is None
    assert job_notification_spec("video.asset.poll", "failed", job_id=job_id) is None


def test_unknown_job_failed():
    job_id = uuid4()
    spec = job_notification_spec("custom.thing", "failed", job_id=job_id, error_message="boom")
    assert spec is not None
    assert spec["type"] == "job.failed"
    assert "boom" in spec["body"]
