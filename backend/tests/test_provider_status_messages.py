"""Poll failures must not leak vendor wording to users."""
from app.provider_errors import public_status_message


def test_moderation_rejection_is_rewritten() -> None:
    out = public_status_message(
        "The request failed because the input image may contain sensitive information",
        fallback="Seedance generation failed",
    )
    assert "sensitive information" not in out
    assert "reference image" in out


def test_other_safety_wordings_are_rewritten() -> None:
    for raw in (
        "Blocked by content policy",
        "NSFW content detected",
        "person_generation not allowed",
    ):
        assert public_status_message(raw, fallback="x") != raw


def test_actionable_provider_text_is_kept() -> None:
    raw = "Duration 11s exceeds the maximum allowed for reference-to-video, which is 10s."
    assert public_status_message(raw, fallback="Grok generation failed") == raw


def test_empty_message_uses_fallback() -> None:
    assert public_status_message(None, fallback="Kling generation failed") == "Kling generation failed"
    assert public_status_message("   ", fallback="Kling generation failed") == "Kling generation failed"
