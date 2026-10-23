"""The branch where the model writes the words needs the rules Polish already has.

Real prompts are "storytime my worst uber ride" and "grwm for a first date" — a
topic, not a script. The two-field composer leaves "What they say" empty, so this
branch handles most traffic while being written as the fallback case. Polish
explicitly refuses to invent dialogue for a scene-only draft; generation does it
anyway, so the guardrails have to live here.
"""
from app.routers.play_video_helpers import (
    _avatar_improvise_rules,
    _build_video_prompt,
    _improvised_word_budget,
)


def _prompt(text: str, *, seconds: int | None = None, face: bool = True) -> str:
    built, _note = _build_video_prompt(
        mode="avatar",
        provider="xai",
        prompt=text,
        has_identity_image=face,
        has_continue=False,
        duration_seconds=seconds,
    )
    return built


def test_word_budget_tracks_the_shared_speech_rate() -> None:
    # raw_speech_seconds is 2.4 words/sec after a 1s open; the budget must agree
    # or the model writes to a length the clip cannot hold.
    assert _improvised_word_budget(4) == 7
    assert _improvised_word_budget(8) == 16
    assert _improvised_word_budget(15) == 33


def test_word_budget_absent_without_a_duration() -> None:
    assert _improvised_word_budget(None) is None
    assert _improvised_word_budget(0) is None


def test_budget_never_collapses_to_nothing() -> None:
    # A 1s clip must still ask for a speakable line, not zero words.
    assert _improvised_word_budget(1) >= 4


def test_improvise_rules_forbid_invented_claims() -> None:
    # Same contract the pre-flight planner uses: never invent offers, prices, or facts.
    text = _avatar_improvise_rules(4).lower()
    for needed in ("offers", "prices", "claims"):
        assert needed in text, needed


def test_improvise_rules_cover_viral_punctuation() -> None:
    text = _avatar_improvise_rules(4).lower()
    assert "hashtags" in text and "emoji" in text


def test_topic_only_prompt_gets_the_rules() -> None:
    # No "says:" anywhere — the shape 27 of 28 real viral prompts take.
    text = _prompt("storytime my worst uber ride ever", seconds=4)
    assert "IMPROVISED LINE" in text
    assert "roughly 7 words" in text


def test_scripted_prompt_does_not_get_the_rules() -> None:
    # The user wrote the words; nothing here should second-guess them.
    text = _prompt("Kitchen island, black tee. says: free shipping ends Friday", seconds=4)
    assert "IMPROVISED LINE" not in text


def test_rules_reach_the_faceless_talking_path() -> None:
    text = _prompt("grwm for a first date", seconds=4, face=False)
    assert "IMPROVISED LINE" in text


def test_longer_clip_earns_a_longer_line() -> None:
    short = _prompt("3 things i wish i knew at 22", seconds=4)
    long = _prompt("3 things i wish i knew at 22", seconds=15)
    assert "roughly 7 words" in short
    assert "roughly 33 words" in long


def test_missing_duration_still_bounds_the_line() -> None:
    text = _prompt("day in my life as a software engineer", seconds=None)
    assert "IMPROVISED LINE" in text
    assert "one short sentence" in text
