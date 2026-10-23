"""Play voices read at natural pace, and preview matches the generated clip."""
from app.voiceover import clamp_speech_speed, speech_speed_for, voiceover_text


def test_default_is_natural_pace() -> None:
    # Lip-sync and preview both call with no override; anything but 1.0 makes the
    # mouth run ahead of a normal read.
    assert speech_speed_for() == 1.0
    assert speech_speed_for(None) == 1.0


def test_explicit_speed_is_honoured() -> None:
    assert speech_speed_for(1.2) == 1.2
    assert speech_speed_for(0.85) == 0.85


def test_speed_is_clamped_to_a_usable_range() -> None:
    assert clamp_speech_speed(9.0) == 1.5
    assert clamp_speech_speed(0.1) == 0.7


def test_script_is_read_as_written() -> None:
    # No injected SSML wrappers: what the user typed is what gets spoken.
    assert voiceover_text("Free shipping this week.") == "Free shipping this week."


def test_domains_are_expanded_for_speech() -> None:
    assert voiceover_text("Visit example.com today") == "Visit example dot com today"
