"""Provider failures must tell users whether retrying can ever work."""
from app.provider_errors import public_provider_error
from app.routers.play_video_helpers import estimate_speech_seconds, raw_speech_seconds


def test_prompt_rejection_is_not_a_try_again_later() -> None:
    status, detail = public_provider_error(
        RuntimeError("Gemini video start failed: prompt blocked by safety filters"),
        kind="media",
    )
    assert status == 422
    assert "try again in a few minutes" not in detail.lower()
    assert "change the wording" in detail.lower()


def test_transient_failure_still_says_try_again() -> None:
    status, detail = public_provider_error(
        RuntimeError("Seedance request failed with HTTP 503"), kind="media"
    )
    # 503, not 502 — Cloudflare replaces an origin 502 with its own error page.
    assert status == 503
    assert "try again" in detail.lower()


def test_missing_config_is_support_message() -> None:
    status, detail = public_provider_error(
        RuntimeError("Kling API key is not configured"), kind="media"
    )
    assert status == 503
    assert "contact support" in detail.lower()


def test_rate_limit_is_busy_message() -> None:
    status, detail = public_provider_error(RuntimeError("HTTP 429 rate limit"), kind="media")
    assert status == 503
    assert "busy" in detail.lower()


def test_speech_estimate_shares_one_rate() -> None:
    """Composer Auto and generate must agree on spoken length."""
    script = " ".join(["word"] * 24)  # 24 / 2.4 + 1 = 11s
    assert abs(raw_speech_seconds(script) - 11.0) < 0.01
    assert estimate_speech_seconds(f"says: {script}", mode="avatar") == 11
    assert raw_speech_seconds("") == 0.0
