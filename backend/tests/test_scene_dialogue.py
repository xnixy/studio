"""Quoted A-scene dialogue: Face vs other speaker, skip signage."""
from __future__ import annotations

from uuid import uuid4

from app.routers.play_scene_dialogue import (
    ensure_other_speaker_gender,
    extract_scene_dialogue,
    normalize_scene_dialogue_order,
    scene_needs_exact_voice,
)
from app.stock_voices import (
    DEFAULT_STOCK_MALE_VOICE_ID,
    DEFAULT_STOCK_VOICE_ID,
    opposite_stock_voice_id,
)

INTERVIEW = (
    "Two people on a Manhattan sidewalk at night. A reporter walks up with a mic and "
    'asks "what brings you out here?" She laughs and says "just testing what Studio can do."'
)

TWO_HANDER = 'Two friends at a cafe. She says "I got the job." He says "I knew you would."'


def test_interview_gives_the_face_the_second_line() -> None:
    lines = extract_scene_dialogue(INTERVIEW, face_gender="female")
    assert [(row.speaker, row.text) for row in lines] == [
        ("other", "what brings you out here?"),
        ("face", "just testing what Studio can do."),
    ]


CAFE_FRIEND_REPLY = (
    "She's at a cafe table, dressed in black yoga pants, talking to a friend. "
    'The friend replies "I didn\'t know, that\'s so cool." '
    '"Do you know you can clone your own voice and reuse it?"'
)


def test_friend_reply_after_she_scene_is_other() -> None:
    lines = extract_scene_dialogue(CAFE_FRIEND_REPLY, face_gender="female")
    assert [row.speaker for row in lines] == ["other", "face"]
    assert "cool" in lines[0].text
    assert "clone" in lines[1].text


def test_cafe_reply_then_question_is_asked_first() -> None:
    ordered = normalize_scene_dialogue_order(CAFE_FRIEND_REPLY)
    assert ordered.index("clone your own voice") < ordered.index("friend replies")
    lines = extract_scene_dialogue(ordered, face_gender="female")
    assert [row.speaker for row in lines] == ["face", "other"]
    assert "clone" in lines[0].text
    assert "cool" in lines[1].text


def test_friend_without_a_look_gets_the_opposite_gender() -> None:
    scene = ensure_other_speaker_gender(
        "She's at a cafe talking to a friend.",
        "male",
    )
    assert "The friend is a man." in scene


def test_two_hander_splits_she_and_he() -> None:
    lines = extract_scene_dialogue(TWO_HANDER, face_gender="female")
    assert [row.speaker for row in lines] == ["face", "other"]
    assert "job" in lines[0].text
    assert "knew" in lines[1].text


def test_male_face_swaps_he_to_the_face() -> None:
    lines = extract_scene_dialogue(TWO_HANDER, face_gender="male")
    assert [row.speaker for row in lines] == ["other", "face"]


def test_unattributed_quote_belongs_to_the_face() -> None:
    lines = extract_scene_dialogue('Kitchen island. "Free shipping this week."')
    assert len(lines) == 1
    assert lines[0].speaker == "face"
    assert "Free shipping" in lines[0].text


def test_signage_quote_is_not_spoken() -> None:
    lines = extract_scene_dialogue(
        'She holds up a sign that reads "OPEN" and says "we are back"'
    )
    assert [row.text for row in lines] == ["we are back"]
    assert lines[0].speaker == "face"


def test_no_line_means_no_exact_voice() -> None:
    assert extract_scene_dialogue("Two friends talk about the new drop") == []
    assert (
        scene_needs_exact_voice(
            face_asset_id=uuid4(),
            continue_from_asset_id=None,
            prompt="Two friends talk about the new drop",
        )
        is False
    )


def test_natural_says_uses_the_selected_voice() -> None:
    prompt = (
        "Makeup room, warm vanity bulbs, black tank. She sits at the table "
        "and says this room is not a set. I picked a Face, typed a line."
    )
    lines = extract_scene_dialogue(prompt, face_gender="female")
    assert len(lines) == 1
    assert lines[0].speaker == "face"
    assert "this room is not a set" in lines[0].text
    assert scene_needs_exact_voice(
        face_asset_id=uuid4(),
        continue_from_asset_id=None,
        prompt=prompt,
    )


def test_needs_face_and_quotes() -> None:
    quoted = 'Cafe. She says "I got the job."'
    assert scene_needs_exact_voice(
        face_asset_id=uuid4(), continue_from_asset_id=None, prompt=quoted
    )
    assert not scene_needs_exact_voice(
        face_asset_id=None, continue_from_asset_id=None, prompt=quoted
    )
    assert scene_needs_exact_voice(
        face_asset_id=uuid4(), continue_from_asset_id=uuid4(), prompt=quoted
    )


def test_opposite_stock_voice_is_the_other_featured_gender() -> None:
    assert opposite_stock_voice_id("female") == DEFAULT_STOCK_MALE_VOICE_ID
    assert opposite_stock_voice_id("male") == DEFAULT_STOCK_VOICE_ID
    assert opposite_stock_voice_id(None) == DEFAULT_STOCK_MALE_VOICE_ID


def test_face_bound_voice_beats_leftover_chip() -> None:
    from app.routers.play_voices import pick_play_voice, play_voice_candidates

    bound = str(uuid4())
    assert pick_play_voice(body_voice="brian", face_bound_voice_id="jessica") == "jessica"
    assert pick_play_voice(body_voice="jessica", face_bound_voice_id=bound) == bound
    assert pick_play_voice(body_voice="brian", face_bound_voice_id=None) == "brian"
    assert pick_play_voice(body_voice=None, face_bound_voice_id=None) == DEFAULT_STOCK_VOICE_ID
    assert pick_play_voice(body_voice="  ", face_bound_voice_id="") == DEFAULT_STOCK_VOICE_ID
    assert play_voice_candidates(body_voice="brian", face_bound_voice_id=bound) == [
        bound,
        "brian",
        DEFAULT_STOCK_VOICE_ID,
    ]
    assert play_voice_candidates(body_voice=bound, face_bound_voice_id=bound) == [
        bound,
        DEFAULT_STOCK_VOICE_ID,
    ]
    assert (
        pick_play_voice(
            body_voice="brian",
            face_bound_voice_id="jessica",
            honor_body_voice=True,
        )
        == "brian"
    )
    assert play_voice_candidates(
        body_voice="brian",
        face_bound_voice_id=bound,
        honor_body_voice=True,
    ) == ["brian", bound, DEFAULT_STOCK_VOICE_ID]


def test_clone_voiceover_is_face_seconds_only() -> None:
    from app.routers.play_scene_voice import clone_voiceover_seconds

    assert clone_voiceover_seconds(0) == 0
    assert clone_voiceover_seconds(2.2) == 5
    assert clone_voiceover_seconds(12.1) == 13
    assert clone_voiceover_seconds(8.0) == 8
