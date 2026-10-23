"""Parser tokens must not reach a provider, and house rules must yield to the scene.

Three separate leaks found by running real prompt shapes through the builders:
lip-sync pronounced "says colon" out loud, quoted signage was read as dialogue,
and an empty marker put the token itself in the SCENE block.
"""
from app.routers.play_video_helpers import (
    TOPIC_ONLY_AUTO_SECONDS,
    _audio_tail,
    _avatar_address_rule,
    _build_video_prompt,
    _scene_speech_rules,
    estimate_speech_seconds,
    split_avatar_user_prompt,
    strip_says_marker,
)


# --- says: normalisation -------------------------------------------------


def test_marker_is_removed_but_both_halves_survive() -> None:
    # A Talking draft carried into another mode. Lip-sync speaks this verbatim.
    assert (
        strip_says_marker("Kitchen island, black tee. says: free shipping ends Friday")
        == "Kitchen island, black tee. free shipping ends Friday"
    )


def test_marker_with_no_scene_keeps_only_the_words() -> None:
    assert strip_says_marker("says: subscribe for more") == "subscribe for more"


def test_marker_with_no_line_keeps_only_the_scene() -> None:
    assert strip_says_marker("Kitchen island, black tee. says:") == "Kitchen island, black tee"


def test_text_without_a_marker_is_untouched() -> None:
    plain = "Hey guys, welcome back to the channel"
    assert strip_says_marker(plain) == plain


def test_empty_marker_no_longer_lands_in_the_scene_block() -> None:
    # Input "says:" used to return the raw text, putting the token in SCENE.
    spoken, scene = split_avatar_user_prompt("says:")
    assert spoken == ""
    assert "says:" not in scene


# --- quoted signage vs dialogue ------------------------------------------


def test_dialogue_rule_separates_written_text_from_speech() -> None:
    text = _scene_speech_rules().lower()
    assert "sign" in text and "not spoken" in text


def test_video_prompt_with_signage_carries_the_carve_out() -> None:
    built, _note = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt='She holds up a sign that reads "OPEN" and says "we are back"',
        has_identity_image=False,
        has_continue=False,
    )
    assert "DIALOGUE:" in built
    assert "not spoken by anyone" in built


# --- house rules that must yield to the scene ----------------------------


def test_address_rule_excludes_bystanders() -> None:
    text = _avatar_address_rule("streets of New York").lower()
    assert "bystanders" in text
    assert "speak to the camera the whole line" in text
    assert "a friend is the listener" not in text


def test_delivery_is_a_default_the_scene_can_override() -> None:
    # A whisper, a rant, and a breakdown all got "relaxed... not rushed" before.
    text = _audio_tail(generate_audio=True, talking=True, provider="xai").lower()
    assert "default" in text and "scene text" in text


def test_dialogue_branch_forbids_speaking_stage_directions() -> None:
    built, _note = _build_video_prompt(
        mode="avatar",
        provider="xai",
        prompt="Doctors office. says: take two of these, then she turns to the nurse",
        has_identity_image=True,
        has_continue=False,
    )
    assert "never pronounced" in built


# --- auto length ---------------------------------------------------------


def test_topic_only_prompt_stops_measuring_the_scene() -> None:
    # "3 things i wish i knew at 22" used to size a 4s clip off the description.
    assert estimate_speech_seconds("3 things i wish i knew at 22") == TOPIC_ONLY_AUTO_SECONDS
    assert estimate_speech_seconds("storytime my worst uber ride ever") == TOPIC_ONLY_AUTO_SECONDS


def test_a_real_line_is_still_measured() -> None:
    short = estimate_speech_seconds("Kitchen. says: free shipping")
    long = estimate_speech_seconds(
        "Kitchen. says: " + " ".join(["word"] * 40)
    )
    assert short < long
    assert long <= 15


def test_non_avatar_modes_measure_the_whole_prompt() -> None:
    assert estimate_speech_seconds("hey guys welcome back", mode="video") >= 4
    assert estimate_speech_seconds("hey guys welcome back", mode="lipsync") >= 4
