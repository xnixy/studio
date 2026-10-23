"""Assist picks Fast vs 2.5 from speech length, not a question."""
from app.routers.play_assist_lane import settle_clip_lane
from app.routers.play_assist_rules import settle_draft
from app.schemas.play import PlayAssistDraft


def test_short_line_stays_fast() -> None:
    model, res, duration, extend_rest, platform = settle_clip_lane(
        kind="avatar",
        scene="Kitchen",
        line="switch serums this week",
    )
    assert model == "seedance-avatar-fast"
    assert res == "720p"
    assert duration <= 15
    assert extend_rest is False
    assert platform is None


def test_sixteen_second_line_uses_25() -> None:
    line = " ".join(["hello"] * 40)
    model, res, duration, extend_rest, _platform = settle_clip_lane(
        kind="avatar",
        scene="",
        line=line,
    )
    assert model == "seedance-avatar"
    assert duration > 15
    assert extend_rest is False


def test_over_thirty_sets_extend_rest() -> None:
    line = " ".join(["hello"] * 90)
    model, _res, duration, extend_rest, _platform = settle_clip_lane(
        kind="avatar",
        scene="",
        line=line,
    )
    assert model == "seedance-avatar"
    assert duration == 30
    assert extend_rest is True


def test_asked_4k_on_short_line_stays_fast() -> None:
    model, res, _duration, _extend, _platform = settle_clip_lane(
        kind="video",
        scene="A city street at night",
        line="",
        last_user="make it 4k",
    )
    assert model == "seedance-2-0-fast"
    assert res == "4k"


def test_asked_4k_on_long_line_drops_to_720p() -> None:
    line = " ".join(["hello"] * 40)
    model, res, _duration, _extend, _platform = settle_clip_lane(
        kind="avatar",
        scene="",
        line=line,
        last_user="4k please",
    )
    assert model == "seedance-avatar"
    assert res == "720p"


def test_settle_draft_writes_lane() -> None:
    draft = settle_draft(
        current=PlayAssistDraft(),
        proposed=PlayAssistDraft(scene="Kitchen", line="hi there friends", kind="avatar"),
        mode="avatar",
        last_user="in the kitchen",
    )
    assert draft.model == "seedance-avatar-fast"
    assert draft.resolution == "720p"
    assert draft.extend_rest is False
