"""The pre-flight planner proposes; the server decides.

Duration follows the spoken line. Assist does not trim words to fit a guessed
length. The says: token is still stripped from draft fields.
"""
from app.routers.play_assist import _parse_reply, _settle_options
from app.routers.play_assist_rules import (
    ASSIST_MAX_TURNS,
    build_summary,
    settle_draft,
    system_prompt,
    transcript_for,
)
from app.schemas.play import PlayAssistDraft, PlayAssistMessage, PlayAssistSource


def _settle(mode: str, **proposed) -> PlayAssistDraft:
    return settle_draft(
        current=PlayAssistDraft(),
        proposed=PlayAssistDraft(**proposed),
        mode=mode,
    )


# --- parsing the reply ---------------------------------------------------


def test_fenced_json_is_read() -> None:
    parsed = _parse_reply('```json\n{"reply": "ok", "ready": true}\n```')
    assert parsed["reply"] == "ok" and parsed["ready"] is True


def test_json_with_prose_around_it_is_read() -> None:
    parsed = _parse_reply('Sure thing. {"reply": "ok"} hope that helps')
    assert parsed["reply"] == "ok"


def test_unparseable_reply_degrades_quietly() -> None:
    # A bad reply must not take the composer down.
    assert _parse_reply("no json here at all") == {}
    assert _parse_reply("") == {}


# --- settling the draft --------------------------------------------------


def test_says_token_never_survives_into_a_field() -> None:
    draft = _settle("avatar", scene="Kitchen. says: hi", line="says: free shipping", duration_seconds=8)
    assert "says:" not in draft.scene
    assert "says:" not in draft.line


def test_talking_line_is_kept_and_length_follows_it() -> None:
    # A short duration guess used to chop the words. Keep the line, size the clip.
    line = " ".join(["word"] * 40)
    draft = _settle("avatar", scene="Kitchen", line=line, duration_seconds=4)
    assert draft.line == line
    assert draft.duration_seconds and draft.duration_seconds > 15
    assert draft.model == "seedance-avatar"


def test_talking_without_a_length_uses_the_topic_default() -> None:
    draft = _settle("avatar", scene="storytime my worst uber ride", line="")
    assert draft.duration_seconds == 8


def test_talking_length_follows_the_line_not_a_guess() -> None:
    assert _settle("avatar", scene="Kitchen", line="hi", duration_seconds=99).duration_seconds == 4
    assert _settle("avatar", scene="Kitchen", line="hi", duration_seconds=1).duration_seconds == 4


def test_talking_without_a_line_still_clamps_a_guessed_length() -> None:
    draft = _settle("avatar", scene="Kitchen", line="", duration_seconds=99)
    assert draft.duration_seconds == 8
    assert draft.model == "seedance-avatar-fast"


def test_lipsync_script_settles_as_talking() -> None:
    script = " ".join(["word"] * 200)
    draft = _settle("lipsync", line=script)
    assert draft.line == script
    assert draft.kind == "avatar"


def test_legacy_lipsync_mode_picks_a_talking_model() -> None:
    draft = _settle("lipsync", line="hey guys welcome back")
    assert draft.duration_seconds is not None
    assert draft.model == "seedance-avatar-fast"


def test_video_mode_has_no_spoken_half() -> None:
    draft = _settle("video", scene="", line="Two friends at a bar arguing")
    assert draft.line == ""
    assert draft.scene.startswith("Two friends at a bar arguing")
    assert "look at the person they are talking to" in draft.scene.lower()


def test_video_mode_drops_a_line_when_a_scene_exists() -> None:
    draft = _settle("video", scene="Two friends at a bar", line="stray dialogue")
    assert draft.line == ""
    assert draft.scene.startswith("Two friends at a bar")
    assert "look at the person they are talking to" in draft.scene.lower()


def test_still_mode_has_no_spoken_half() -> None:
    assert _settle("image", scene="Matte black bottle on concrete", line="anything").line == ""


def test_voice_is_carried_from_the_composer_not_the_model() -> None:
    draft = settle_draft(
        current=PlayAssistDraft(voice="ara"),
        proposed=PlayAssistDraft(scene="Kitchen", line="hi", voice="rex"),
        mode="avatar",
    )
    assert draft.voice == "ara"


# --- what the user is shown ----------------------------------------------


def test_summary_states_mode_and_length() -> None:
    bits = build_summary(PlayAssistDraft(scene="Kitchen", line="hi", duration_seconds=8), mode="avatar")
    assert "Talking" in bits and "~8s" in bits


def test_summary_includes_fast_by_default() -> None:
    bits = build_summary(
        PlayAssistDraft(scene="storytime", line="hi", duration_seconds=8, model="seedance-avatar-fast"),
        mode="avatar",
    )
    assert "Fast" in bits


# --- prompting -----------------------------------------------------------


def test_system_prompt_forbids_invented_facts() -> None:
    text = system_prompt("avatar").lower()
    assert "never invent offers, prices" in text


def test_system_prompt_limits_questions() -> None:
    text = system_prompt("avatar").lower()
    assert "at most one question" in text
    assert "prefer stating an assumption" in text


def test_last_exchange_stops_the_questions() -> None:
    assert "last exchange" in system_prompt("avatar", forced_ready=True).lower()
    assert "last exchange" not in system_prompt("avatar").lower()


def test_talking_rules_keep_the_line_spoken() -> None:
    text = system_prompt("avatar").lower()
    assert "never cut, trim, or shorten the line" in text


def test_talking_assist_does_not_rewrite_a_conversation_as_a_talking_head() -> None:
    text = system_prompt("avatar").lower()
    assert "look at that person, not past them and not at the camera" in text
    assert "one person on camera" not in text
    assert "never cut, trim, or shorten the line" in text
    assert "shot at eye level" in text
    assert "do not write a shot list" in text


def test_cafe_draft_adds_a_look_sentence_without_a_shot_list() -> None:
    draft = _settle(
        "avatar",
        scene="She's at a cafe table in a yellow top, talking to a friend across from her",
        line="I got the job. I still can't believe I said yes.",
    )
    assert "yellow top" in draft.scene
    assert "look at the person they are talking to" in draft.scene.lower()
    assert "not past them" in draft.scene.lower()
    assert "shot at eye level" in draft.scene.lower()
    assert "3/4" not in draft.scene
    assert "bokeh" not in draft.scene
    assert "portrait blur" not in draft.scene


def test_solo_desk_draft_gets_a_default_shot_without_a_listener() -> None:
    draft = _settle("avatar", scene="Desk, soft window light, black hoodie", line="free shipping this week")
    assert "shot at eye level" in draft.scene.lower()
    assert "face large in the frame" in draft.scene.lower()
    assert "look at the person they are talking to" not in draft.scene.lower()


def test_named_camera_is_not_overwritten_by_assist() -> None:
    draft = _settle(
        "avatar",
        scene="Drone view of the boardwalk, full figure, white sneakers",
        line="just testing the new update",
    )
    assert "drone view" in draft.scene.lower()
    assert "full figure" in draft.scene.lower()
    assert "eye-level" not in draft.scene.lower()


def test_scene_job_does_not_get_the_talking_shot_default() -> None:
    draft = _settle(
        "video",
        scene='Two friends at a cafe. She says "I got the job." He says "I knew you would."',
    )
    assert "look at the person they are talking to" in draft.scene.lower()
    assert "not past them" in draft.scene.lower()
    assert "3/4" not in draft.scene
    assert "eye-level" not in draft.scene.lower()


def test_look_at_each_other_is_already_a_look_sentence() -> None:
    draft = _settle(
        "video",
        scene="She's at a cafe table, talking to a friend. They look at each other, not the camera.",
    )
    assert "look at each other" in draft.scene.lower()
    assert "look at the person they are talking to" not in draft.scene.lower()


def test_existing_look_sentence_is_not_duplicated() -> None:
    scene = (
        "Cafe table, talking to a friend. They look at the person they are talking to, "
        "not past them and not at the camera."
    )
    draft = _settle("avatar", scene=scene, line="hey")
    assert draft.scene.lower().count("not past them") == 1


def test_video_assist_keeps_conversational_eyeline() -> None:
    text = system_prompt("video").lower()
    assert "look at the person they are talking to" in text
    assert "not past them" in text
    assert "shot list" in text


def test_transcript_states_the_draft_before_the_conversation() -> None:
    turns = transcript_for(
        PlayAssistDraft(scene="Kitchen", line="", duration_seconds=8),
        [PlayAssistMessage(role="user", content="make it funnier")],
        mode="avatar",
    )
    assert turns[0]["role"] == "user"
    assert "Scene: Kitchen" in turns[0]["content"]
    assert "Line: (none yet)" in turns[0]["content"]
    assert turns[-1]["content"] == "make it funnier"


def test_turn_cap_is_small_enough_to_stay_out_of_the_way() -> None:
    assert ASSIST_MAX_TURNS <= 3


# --- offered choices -----------------------------------------------------


def test_choices_come_back_with_the_pick_applied() -> None:
    opts = _settle_options(
        {
            "header": "Eyeline",
            "choices": [
                {"label": "To camera", "value": "she talks to camera", "selected": True},
                {"label": "To her friend", "value": "she talks to her friend"},
            ],
        }
    )
    assert opts is not None
    assert opts.choices[0].selected is True


def test_a_pick_is_forced_when_the_planner_forgets_one() -> None:
    # Without a selection this reads as a question that blocks, which is the one
    # thing options must never be.
    opts = _settle_options(
        {"header": "Eyeline", "choices": [{"label": "To camera"}, {"label": "To her friend"}]}
    )
    assert opts is not None
    assert opts.choices[0].selected is True


def test_a_single_choice_is_not_offered() -> None:
    # One option is a label pretending to be a decision.
    assert _settle_options({"header": "Eyeline", "choices": [{"label": "To camera"}]}) is None


def test_malformed_options_never_break_the_card() -> None:
    assert _settle_options(None) is None
    assert _settle_options({"choices": []}) is None
    assert _settle_options({"header": "Eyeline"}) is None
    assert _settle_options("nonsense") is None


def test_choices_are_capped_so_the_card_stays_a_card() -> None:
    opts = _settle_options(
        {
            "header": "Eyeline",
            "choices": [{"label": f"opt {i}"} for i in range(9)],
        }
    )
    assert opts is not None
    assert len(opts.choices) <= 4


def test_planner_is_told_options_are_optional() -> None:
    text = system_prompt("avatar").lower()
    assert "omit it when nothing is genuinely open" in text


# --- following on from an existing clip ----------------------------------


def test_continue_keeps_the_look_and_moves_the_story() -> None:
    text = system_prompt("video", source_kind="continue").lower()
    assert "not a repeat" in text
    assert "same person, place, wardrobe" in text


def test_revoice_is_script_only() -> None:
    # Every word is read aloud, so a camera note becomes dialogue.
    text = system_prompt("avatar", source_kind="revoice").lower()
    assert "only the script changes" in text


def test_retry_works_from_the_failure_reason() -> None:
    text = system_prompt("avatar", source_kind="retry").lower()
    assert "say plainly what you changed" in text
    # A provider outage is not a prompt problem; guessing at one wastes a turn.
    assert "not something a prompt can fix" in text


def test_no_source_adds_no_follow_on_rules() -> None:
    plain = system_prompt("avatar")
    assert "not a repeat" not in plain
    assert "only the script changes" not in plain


def test_transcript_states_the_previous_clip() -> None:
    turns = transcript_for(
        PlayAssistDraft(),
        [],
        mode="video",
        source=PlayAssistSource(kind="continue", prompt="She walks into the kitchen"),
    )
    assert "Previous clip: She walks into the kitchen" in turns[0]["content"]


def test_transcript_states_why_a_retry_failed() -> None:
    turns = transcript_for(
        PlayAssistDraft(),
        [],
        mode="avatar",
        source=PlayAssistSource(kind="retry", prompt="Kitchen", error="Content policy rejected"),
    )
    assert "It failed with: Content policy rejected" in turns[0]["content"]


def test_failure_reason_is_only_stated_for_a_retry() -> None:
    # A continue carrying a stale error would send the planner chasing a fix
    # for something that already worked.
    turns = transcript_for(
        PlayAssistDraft(),
        [],
        mode="video",
        source=PlayAssistSource(kind="continue", prompt="Kitchen", error="old failure"),
    )
    assert "old failure" not in turns[0]["content"]


# --- short-form formats --------------------------------------------------


def test_planner_knows_the_formats_people_actually_type() -> None:
    # Read literally, "pov: ur crush texts back" became a person standing in a
    # place called pov. These are shapes with staging, not descriptions.
    text = system_prompt("avatar").lower()
    for fmt in ("pov", "grwm", "storytime", "day in my life", "part 2"):
        assert fmt in text, fmt


def test_format_labels_are_kept_out_of_the_generated_text() -> None:
    text = system_prompt("avatar").lower()
    assert "never put the label itself, a hashtag, or an @handle" in text


def test_explicit_staging_still_beats_the_format_default() -> None:
    assert "their wording wins" in system_prompt("avatar").lower()


def test_formats_reach_every_mode() -> None:
    # A pov still and a pov clip are the same framing idea.
    for mode in ("avatar", "video", "image"):
        assert "pov is a first person" in system_prompt(mode).lower(), mode
