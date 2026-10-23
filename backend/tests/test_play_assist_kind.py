"""Clip kind is rule-based. Grok does not pick the engine."""
import re

from app.routers.play_assist_kind import (
    KIND_AVATAR,
    KIND_VIDEO,
    build_clip_reply,
    classify_clip_kind,
    clip_kind_options,
    is_kind_chip,
    line_draft_system_prompt,
    merge_clip_fields,
    needs_line_draft,
    parse_kind_chip,
    split_clip_blob,
)
from app.schemas.play import PlayAssistDraft, PlayAssistSource


def test_chip_values_are_parseable() -> None:
    assert parse_kind_chip("kind:lipsync") == KIND_AVATAR
    assert is_kind_chip("kind:avatar")
    assert not is_kind_chip("keep this photo")


def test_chip_tap_legacy_photo_becomes_talking() -> None:
    kind = classify_clip_kind(
        last_user="kind:lipsync",
        draft=PlayAssistDraft(scene="Kitchen", line="switch serums", kind=KIND_AVATAR),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_follow_up_keeps_the_kind() -> None:
    kind = classify_clip_kind(
        last_user="make it funnier",
        draft=PlayAssistDraft(scene="Kitchen", line="switch serums", kind=KIND_AVATAR),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_script_without_a_place_is_talking() -> None:
    script = "I actually finish these protein bars. Not chalky, not too sweet, and they keep me full until lunch."
    kind = classify_clip_kind(
        last_user=script,
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_topic_plus_place_is_you_talking() -> None:
    kind = classify_clip_kind(
        last_user="Kitchen counter, morning light. Talk about the serum.",
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_two_quoted_speakers_are_a_scene() -> None:
    kind = classify_clip_kind(
        last_user='Cafe. She says "I got the job." He says "I knew you would."',
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_VIDEO


def test_friend_replies_is_a_scene() -> None:
    kind = classify_clip_kind(
        last_user=(
            "She's at a cafe talking to a friend. The friend replies "
            '"I didn\'t know, that\'s so cool."'
        ),
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_VIDEO


def test_one_quote_talking_to_a_friend_stays_you_talking() -> None:
    kind = classify_clip_kind(
        last_user=(
            'She\'s at a cafe talking to a friend. "Do you know you can clone '
            'your own voice and reuse it?"'
        ),
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


CAFE_TWO_HANDER = (
    "She's at a cafe table, dressed in black yoga pants and casual white sneakers, "
    "talking to a friend across from her. The friend wears a denim jacket. They look "
    'at each other, not the camera. The friend replies “I didn’t know, that’s so cool.”. '
    "Do you know you can clone your own voice and reuse it?"
)


def test_cafe_two_hander_keeps_both_lines_in_scene() -> None:
    kind = classify_clip_kind(
        last_user=CAFE_TWO_HANDER,
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_VIDEO
    scene, line = split_clip_blob(CAFE_TWO_HANDER, KIND_VIDEO)
    assert line == ""
    assert "yoga pants" in scene
    assert "so cool" in scene
    assert "clone your own voice" in scene
    quotes = re.findall(r'["“]([^"“”]+)["”]', scene)
    assert len(quotes) >= 2
    assert "clone your own voice" in quotes[0]
    assert "so cool" in quotes[1]
    from app.routers.play_scene_dialogue import extract_scene_dialogue

    spoken = extract_scene_dialogue(scene, face_gender="female")
    assert [row.speaker for row in spoken] == ["face", "other"]
    assert "clone" in spoken[0].text
    assert "cool" in spoken[1].text
    assert scene.index("clone your own voice") < scene.index("friend replies")


def test_video_two_hander_keeps_quote_order() -> None:
    blob = 'Cafe. She says "I got the job." He says "I knew you would."'
    scene, line = split_clip_blob(blob, KIND_VIDEO)
    assert line == ""
    assert scene.index("I got the job") < scene.index("I knew you would")
    assert scene == blob


def test_keep_this_photo_is_talking() -> None:
    kind = classify_clip_kind(
        last_user="Keep this photo and say exactly I finish these bars",
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_extend_stays_a_scene() -> None:
    kind = classify_clip_kind(
        last_user="She walks to the window",
        draft=PlayAssistDraft(),
        request_mode="avatar",
        source=PlayAssistSource(kind="continue", prompt="She walks into the kitchen"),
    )
    assert kind == KIND_VIDEO


def test_revoice_stays_talking() -> None:
    kind = classify_clip_kind(
        last_user="New line about the serum",
        draft=PlayAssistDraft(),
        request_mode="avatar",
        source=PlayAssistSource(kind="revoice", prompt="old line"),
    )
    assert kind == KIND_AVATAR


def test_legacy_lipsync_mode_becomes_talking() -> None:
    kind = classify_clip_kind(
        last_user="Two friends at a bar",
        draft=PlayAssistDraft(),
        request_mode="lipsync",
    )
    assert kind == KIND_AVATAR


def test_place_then_words_splits_for_talking() -> None:
    scene, line = split_clip_blob(
        "Kitchen counter, morning light. If your serum still stings, switch now.",
        KIND_AVATAR,
    )
    assert "Kitchen" in scene
    assert "serum" in line
    assert "Kitchen" not in line


def test_first_person_script_without_a_place_is_the_line() -> None:
    scene, line = split_clip_blob("I finish these protein bars every morning.", KIND_AVATAR)
    assert scene == ""
    assert "protein bars" in line


def test_legacy_photo_chip_keeps_the_draft() -> None:
    scene, line = merge_clip_fields(
        kind="lipsync",
        draft=PlayAssistDraft(scene="Kitchen", line="switch serums", kind=KIND_AVATAR),
        last_user="kind:lipsync",
    )
    assert scene == "Kitchen"
    assert line == "switch serums"


def test_kind_chips_are_talking_and_scene() -> None:
    opts = clip_kind_options(KIND_AVATAR)
    labels = [c.label for c in opts.choices]
    assert labels == ["Talking", "Scene"]
    assert opts.choices[0].selected is True
    assert opts.choices[1].selected is False


def test_needs_a_line_draft_only_for_talking_without_words() -> None:
    assert needs_line_draft(KIND_AVATAR, PlayAssistDraft(scene="Kitchen")) is True
    assert needs_line_draft(KIND_AVATAR, PlayAssistDraft(line="hi")) is False
    assert needs_line_draft("lipsync", PlayAssistDraft()) is False


def test_line_draft_asks_for_a_look_sentence_not_a_shot_list() -> None:
    text = line_draft_system_prompt().lower()
    assert "look at that person, not past them and not at the camera" in text
    assert "shot list" in text
    assert "never cut, trim, or shorten the line" in text


def test_reply_has_no_em_dash() -> None:
    text = build_clip_reply(
        PlayAssistDraft(scene="Kitchen", line="switch serums", kind=KIND_AVATAR),
        kind=KIND_AVATAR,
    )
    assert "—" not in text and "–" not in text
    assert "talking clip" in text.lower()
    assert "Kitchen" not in text


PROTEIN_BAR_PROMPT = (
    "shes dressed in yoga pants and a yoga tank top, she's holding a protein bar "
    "in the hand while sitting at the kitchen table, and says I actually finish "
    "these protein bars. Not chalky, not too sweet, and they keep me full until lunch."
)
PROTEIN_BAR_LINE = (
    "I actually finish these protein bars. Not chalky, not too sweet, "
    "and they keep me full until lunch."
)


def test_natural_and_says_keeps_the_full_protein_bar_line() -> None:
    scene, line = split_clip_blob(PROTEIN_BAR_PROMPT, KIND_AVATAR)
    assert line == PROTEIN_BAR_LINE
    assert "yoga pants" in scene
    assert "kitchen table" in scene
    assert "protein bar" in scene
    assert "says" not in scene.lower()
    assert "I actually finish" not in scene
    assert "chalky" not in scene


def test_she_says_keeps_later_sentences_of_the_line() -> None:
    scene, line = split_clip_blob(
        "Kitchen table, yoga tank. She says I actually finish these protein bars. "
        "Not chalky, not too sweet.",
        KIND_AVATAR,
    )
    assert line == "I actually finish these protein bars. Not chalky, not too sweet."
    assert "Kitchen table" in scene
    assert "says" not in scene.lower()
    assert "I actually finish" not in scene


def test_quoted_line_extracts_the_full_speech() -> None:
    scene, line = split_clip_blob(
        'Yoga pants at the kitchen table. "I actually finish these protein bars. '
        'Not chalky, not too sweet, and they keep me full until lunch."',
        KIND_AVATAR,
    )
    assert line == PROTEIN_BAR_LINE
    assert "kitchen table" in scene
    assert "chalky" not in scene


def test_a_given_line_does_not_need_grok() -> None:
    scene, line = merge_clip_fields(
        kind=KIND_AVATAR,
        draft=PlayAssistDraft(),
        last_user=PROTEIN_BAR_PROMPT,
    )
    draft = PlayAssistDraft(scene=scene, line=line, kind=KIND_AVATAR)
    assert needs_line_draft(KIND_AVATAR, draft) is False
    assert line == PROTEIN_BAR_LINE


def test_reply_does_not_dump_or_truncate_the_scene() -> None:
    scene, line = split_clip_blob(PROTEIN_BAR_PROMPT, KIND_AVATAR)
    text = build_clip_reply(
        PlayAssistDraft(scene=scene, line=line, kind=KIND_AVATAR),
        kind=KIND_AVATAR,
    )
    assert "Talking clip, this line" in text
    assert "You talking in" not in text
    assert "protein bar in t" not in text
    assert "yoga pants" not in text
    assert "says:" not in text
    assert "—" not in text and "–" not in text


def test_video_keeps_natural_speech_inside_the_scene() -> None:
    scene, line = split_clip_blob(PROTEIN_BAR_PROMPT, KIND_VIDEO)
    assert line == ""
    assert "yoga pants" in scene
    assert "I actually finish" in scene
    assert scene.count('"') >= 2


def test_chip_tap_a_scene_puts_the_question_before_the_reply() -> None:
    scene, line = merge_clip_fields(
        kind=KIND_VIDEO,
        draft=PlayAssistDraft(
            scene=(
                "Cafe table. The friend replies \"I didn't know, that's so cool.\""
            ),
            line="Do you know you can clone your own voice and reuse it?",
            kind=KIND_AVATAR,
        ),
        last_user="kind:video",
    )
    assert line == ""
    assert scene.index("clone your own voice") < scene.index("friend replies")


def test_chip_tap_a_scene_folds_the_spoken_line_into_scene() -> None:
    scene, line = merge_clip_fields(
        kind=KIND_VIDEO,
        draft=PlayAssistDraft(scene="Kitchen", line="switch serums", kind=KIND_AVATAR),
        last_user="kind:video",
    )
    assert line == ""
    assert "Kitchen" in scene
    assert "switch serums" in scene
    assert '"switch serums"' in scene


def test_chip_tap_a_scene_with_line_only_still_has_a_scene() -> None:
    scene, line = merge_clip_fields(
        kind=KIND_VIDEO,
        draft=PlayAssistDraft(scene="", line="I finish these bars every morning.", kind=KIND_AVATAR),
        last_user="kind:video",
    )
    assert line == ""
    assert "I finish these bars" in scene
    assert scene.startswith('"')


def test_line_draft_miss_turns_talking_into_a_scene() -> None:
    from app.routers.play_assist import fallback_when_line_draft_fails

    kind, draft = fallback_when_line_draft_fails(
        kind=KIND_AVATAR,
        draft=PlayAssistDraft(scene="Kitchen, morning light", line="", kind=KIND_AVATAR),
        last_user="Kitchen, morning light. Talk about the serum.",
    )
    assert kind == KIND_VIDEO
    assert draft.kind == KIND_VIDEO
    assert "Kitchen" in draft.scene
    assert draft.line == ""


def test_line_draft_miss_keeps_talking_when_a_line_exists() -> None:
    from app.routers.play_assist import fallback_when_line_draft_fails

    kind, draft = fallback_when_line_draft_fails(
        kind=KIND_AVATAR,
        draft=PlayAssistDraft(scene="Kitchen", line="switch serums", kind=KIND_AVATAR),
        last_user="Kitchen. Talk about the serum.",
    )
    assert kind == KIND_AVATAR
    assert draft.line == "switch serums"


MAKEUP_ROOM_PROMPT = (
    "Makeup room, warm vanity bulbs, black tank. She sits at the table and "
    "blends blush on her cheek with a brush, talking to the viewer, and says "
    "this room is not a set. I picked a Face, typed a line, and Studio made the "
    "clip. Talking, a scene with a friend, or a still. Same Face."
)


def test_listing_talking_scene_still_stays_talking() -> None:
    """Saying the product kinds in the line is not a Scene job."""
    kind = classify_clip_kind(
        last_user=MAKEUP_ROOM_PROMPT,
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR
    scene, line = split_clip_blob(MAKEUP_ROOM_PROMPT, KIND_AVATAR)
    assert "this room is not a set" in line
    assert "Makeup room" in scene
    assert "a scene with a friend" in line
    assert needs_line_draft(KIND_AVATAR, PlayAssistDraft(scene=scene, line=line)) is False


def test_chip_tap_talking_recovers_a_line_folded_into_scene() -> None:
    folded, _empty = split_clip_blob(MAKEUP_ROOM_PROMPT, KIND_VIDEO)
    scene, line = merge_clip_fields(
        kind=KIND_AVATAR,
        draft=PlayAssistDraft(scene=folded, line="", kind=KIND_VIDEO),
        last_user="kind:avatar",
    )
    assert line
    assert "this room is not a set" in line
    assert "Makeup room" in scene


def test_legacy_photo_chip_recovers_a_line_folded_into_scene() -> None:
    folded, _empty = split_clip_blob(MAKEUP_ROOM_PROMPT, KIND_VIDEO)
    scene, line = merge_clip_fields(
        kind="lipsync",
        draft=PlayAssistDraft(scene=folded, line="", kind=KIND_VIDEO),
        last_user="kind:lipsync",
    )
    assert line
    assert "this room is not a set" in line
    assert "Makeup room" in scene
    assert line != folded


def test_legacy_photo_chip_does_not_copy_wardrobe_when_there_is_no_line() -> None:
    scene, line = merge_clip_fields(
        kind="lipsync",
        draft=PlayAssistDraft(scene="Kitchen, black tank, yoga pants", line="", kind=KIND_VIDEO),
        last_user="kind:lipsync",
    )
    assert scene == "Kitchen, black tank, yoga pants"
    assert line == ""


def test_assist_does_not_extract_says_that() -> None:
    scene, line = split_clip_blob(
        "She says that the lights are too warm for this look.",
        KIND_AVATAR,
    )
    assert not line
    assert "that the lights" in scene.lower()


def test_assist_skips_signage_then_keeps_the_spoken_quote() -> None:
    scene, line = split_clip_blob(
        'She holds up a sign that reads "OPEN" and says "we are back"',
        KIND_AVATAR,
    )
    assert line == "we are back"
    assert "OPEN" not in line


def test_assist_recovers_a_short_spoken_quote() -> None:
    scene, line = split_clip_blob('Kitchen. She looks over and says "hey."', KIND_AVATAR)
    assert line.lower().rstrip(".") == "hey"
    assert "Kitchen" in scene


def test_dont_make_a_scene_stays_talking() -> None:
    kind = classify_clip_kind(
        last_user="Don't make a scene, just say hello",
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_signage_plus_one_spoken_quote_is_not_a_two_hander() -> None:
    kind = classify_clip_kind(
        last_user='She holds a sign that reads "OPEN" and says "we are back"',
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_follow_up_keeps_the_talking_line() -> None:
    scene, line = merge_clip_fields(
        kind=KIND_AVATAR,
        draft=PlayAssistDraft(scene="Kitchen", line="I finish these bars", kind=KIND_AVATAR),
        last_user="make it shorter",
    )
    assert "finish these bars" in line
    assert "shorter" in scene


def test_follow_up_appends_to_a_scene() -> None:
    scene, line = merge_clip_fields(
        kind=KIND_VIDEO,
        draft=PlayAssistDraft(scene="Two friends at a cafe", line="", kind=KIND_VIDEO),
        last_user="make it rain",
    )
    assert line == ""
    assert "cafe" in scene.lower()
    assert "rain" in scene.lower()


def test_crowd_behind_her_is_not_a_two_hander() -> None:
    kind = classify_clip_kind(
        last_user=(
            "She's on a yoga mat, people in the background, and she says "
            "none of this is real."
        ),
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_AVATAR


def test_a_man_who_asks_is_a_scene() -> None:
    kind = classify_clip_kind(
        last_user=(
            "She's on a yoga mat and she says none of this is real. "
            "A man comes to her and asks am I real?"
        ),
        draft=PlayAssistDraft(),
        request_mode="avatar",
    )
    assert kind == KIND_VIDEO
    scene, line = split_clip_blob(
        "She's on a yoga mat and she says none of this is real. "
        "A man comes to her and asks am I real?",
        KIND_VIDEO,
    )
    assert line == ""
    assert "none of this is real" in scene
    assert "am I real" in scene

