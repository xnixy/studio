"""Tests for Play talking prompt split (scene + says: line) and identity prompts."""
from app.routers.play_video_helpers import (
    _avatar_identity_rules,
    _build_video_prompt,
    _scene_names_clothes,
    split_avatar_user_prompt,
)


def test_split_avatar_prompt_with_says() -> None:
    spoken, scene = split_avatar_user_prompt(
        "Kitchen island, soft daylight, black tee. She says: free shipping this week only."
    )
    assert spoken == "free shipping this week only."
    assert "Kitchen island" in scene
    assert "black tee" in scene
    assert "says" not in scene.lower()
    assert not scene.lower().endswith("she")
    assert " she" not in f" {scene.lower()} "


def test_split_avatar_prompt_leans_and_says() -> None:
    spoken, scene = split_avatar_user_prompt(
        "Home office, soft window light, navy hoodie. He leans toward the camera and says: free shipping this week only. Order before midnight and it ships today."
    )
    assert spoken.startswith("free shipping this week only")
    assert "Home office" in scene
    assert "navy hoodie" in scene
    assert "says" not in scene.lower()
    assert "leans" not in scene.lower()
    assert not scene.lower().rstrip(".").endswith("he")


def test_split_avatar_prompt_and_she_says() -> None:
    spoken, scene = split_avatar_user_prompt(
        "shes dressed in yoga pants at the kitchen table and she says "
        "I actually finish these protein bars."
    )
    assert spoken.startswith("I actually finish these protein bars")
    assert "yoga pants" in scene
    assert "says" not in scene.lower()


def test_split_avatar_prompt_she_says_after_a_question() -> None:
    spoken, scene = split_avatar_user_prompt(
        "Kitchen table, yoga pants. Did you hear that? She says we should go."
    )
    assert spoken == "we should go."
    assert "Kitchen table" in scene
    assert "Did you hear that" in scene


def test_split_avatar_prompt_does_not_latch_onto_the_last_and_says() -> None:
    """A man who asks is Scene. Talking must not TTS only the closing 'thats Studio'."""
    from app.routers.play_assist_kind import KIND_VIDEO, classify_clip_kind, split_clip_blob
    from app.schemas.play import PlayAssistDraft

    text = (
        "She’s sitting on the grass on the yoga mat in yoga pants and yoga black "
        "tank top, there are multiple people in background and she says did you know "
        "that none of this real? And then a man comes  to her and asks am I real? "
        "She says no then a women comes to her and asks am I real and she says no, "
        "then she looks back at the camera and says thats Studio"
    )
    kind = classify_clip_kind(
        last_user=text, draft=PlayAssistDraft(), request_mode="avatar"
    )
    assert kind == KIND_VIDEO
    scene, line = split_clip_blob(text, KIND_VIDEO)
    assert line == ""
    assert "thats Studio" in scene
    assert "am I real" in scene
    assert "did you know" in scene


def test_split_avatar_prompt_and_says_without_a_comma() -> None:
    spoken, scene = split_avatar_user_prompt(
        "Makeup room, warm vanity bulbs, black tank. She sits at the table "
        "and says this room is not a set."
    )
    assert spoken.startswith("this room is not a set")
    assert "Makeup room" in scene
    assert "says" not in scene.lower()


def test_split_avatar_prompt_natural_and_says_keeps_full_line() -> None:
    spoken, scene = split_avatar_user_prompt(
        "shes dressed in yoga pants and a yoga tank top, she's holding a protein bar "
        "in the hand while sitting at the kitchen table, and says I actually finish "
        "these protein bars. Not chalky, not too sweet, and they keep me full until lunch."
    )
    assert spoken.startswith("I actually finish these protein bars")
    assert "Not chalky" in spoken
    assert "yoga pants" in scene
    assert "kitchen table" in scene
    assert "says" not in scene.lower()
    assert "finish these" not in scene


def test_named_clothes_override_the_photo_outfit() -> None:
    prompt, _note = _build_video_prompt(
        mode="avatar",
        provider="xai",
        prompt=(
            "Kitchen table, yoga pants and a yoga tank top. says: "
            "I actually finish these protein bars."
        ),
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=8,
        voice="ara",
    )
    lower = prompt.lower()
    assert "this scene names clothes" in lower
    assert "wear the clothes the scene names" in lower
    assert "not the outfit in the photo" in lower
    assert "take the photo clothes off" not in lower
    assert "face, hair, skin, makeup only" in lower
    assert "yoga pants" in lower
    assert "unnamed clothes go on the selected face" in lower


def test_friend_clothes_stay_on_the_friend() -> None:
    from app.routers.play_video_helpers import _avatar_wardrobe_rule

    text = _avatar_wardrobe_rule(
        "Her friend in a red dress sits across the table. She wears a gray tee."
    ).lower()
    assert "friend's outfit stays on the friend" in text
    assert "not the selected face" in text


def test_color_top_counts_as_named_clothes() -> None:
    assert _scene_names_clothes("She's at a cafe table in a yellow top") is True
    assert _scene_names_clothes("soft pink top, bathroom counter") is True
    assert _scene_names_clothes("laptop on top of the table") is False
    assert _scene_names_clothes("the top of the fridge") is False


def test_split_avatar_prompt_no_marker_is_scene_only() -> None:
    """Place or description with no speech verb is scene, not a spoken line."""
    text = "Just a talking head in a bright room with soft light."
    spoken, scene = split_avatar_user_prompt(text)
    assert spoken == ""
    assert scene == text


def test_split_avatar_prompt_first_person_is_the_line() -> None:
    spoken, scene = split_avatar_user_prompt("hey welcome back to the channel")
    assert spoken == "hey welcome back to the channel"
    assert scene == ""
    spoken2, _ = split_avatar_user_prompt("I'm at a cafe")
    assert spoken2 == "I'm at a cafe"


def test_split_avatar_prompt_say_exactly_drops_the_meta() -> None:
    spoken, scene = split_avatar_user_prompt(
        "keep this photo and say exactly welcome back"
    )
    assert spoken == "welcome back"
    assert "keep this photo" in scene
    assert "exactly" not in spoken


def test_avatar_prompt_without_says_does_not_speak_the_scene() -> None:
    """Regression: the scene description must never become the spoken line."""
    scene_text = "Kitchen island, soft daylight, black tee, talking about free shipping this week"
    prompt, _note = _build_video_prompt(
        mode="avatar",
        provider="xai",
        prompt=scene_text,
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=8,
        voice="leo",
    )
    assert f'"{scene_text}"' not in prompt
    assert "in your own words" in prompt
    assert "Never read the scene description" in prompt
    # The scene itself still reaches the model.
    assert "Kitchen island" in prompt


def test_split_avatar_prompt_empty() -> None:
    assert split_avatar_user_prompt("") == ("", "")
    assert split_avatar_user_prompt("   ") == ("", "")


def test_avatar_identity_prompt_overrides_photo_background() -> None:
    prompt, note = _build_video_prompt(
        mode="avatar",
        provider="xai",
        prompt="Neon Tokyo street at night, rain, leather jacket. She says: check the drop tonight.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=5,
        voice="ara",
    )
    lower = prompt.lower()
    assert "neon tokyo" in lower
    assert "check the drop tonight" in lower
    assert "identity lock" in lower or "identity" in lower
    assert "different person" in lower or "same person" in lower or "same human" in lower
    assert "scene" in lower
    assert note is not None
    assert "identity" in note.lower()


def test_avatar_identity_prompt_seedance_uses_image_tag() -> None:
    prompt, _note = _build_video_prompt(
        mode="avatar",
        provider="seedance",
        prompt="Kitchen island, black tee. He says: free shipping this week.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=5,
        voice="rex",
    )
    assert "@Image1" in prompt
    assert "Kitchen island" in prompt
    assert "free shipping this week" in prompt
    # Speech block must use the same tag, not a generic "reference image".
    assert "SAME person from @Image1" in prompt
    # Audio tail already covers second narrator; do not stack it in the pace block.
    assert prompt.count("No second narrator") == 1
    # Duration in the prompt is the request value (here 5 from the test fixture).
    assert "exactly 5 seconds" in prompt


def test_identity_rules_sentence_case() -> None:
    text = _avatar_identity_rules(image_tag="the first reference image")
    assert "Treat the first reference image as the identity ground truth" in text
    # Avoid a lowercase sentence start like "the first reference image is the identity…"
    assert "ethnicity. the first" not in text


def test_grok_talking_binds_image_and_voice_tags() -> None:
    prompt, _note = _build_video_prompt(
        mode="avatar",
        provider="xai",
        prompt="Kitchen, black tee. She says: hello free shipping.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=15,
        voice="eve",
    )
    assert "<IMAGE_1>" in prompt
    assert "<AUDIO_0>" in prompt
    assert "the first reference image" not in prompt


def test_avatar_speech_uses_provider_image_tag() -> None:
    expected = {
        "xai": "<IMAGE_1>",
        "seedance": "@Image1",
        "gemini": "the reference face image",
        "kling": "the input image",
    }
    for provider, tag in expected.items():
        prompt, _note = _build_video_prompt(
            mode="avatar",
            provider=provider,
            prompt="Kitchen, black tee. She says: hello free shipping.",
            has_identity_image=True,
            has_continue=False,
            generate_audio=True,
            duration_seconds=5,
            voice="ara",
        )
        assert f"SAME person from {tag}" in prompt, provider


def test_avatar_continue_splits_says_and_locks_identity() -> None:
    """Continue must not dump raw 'says:' and should keep identity + quoted line."""
    user = (
        "Bathroom mirror, soft morning light, white tank top. says: "
        "If your under-eye cream still creases by noon, switch."
    )
    for provider in ("xai", "seedance", "gemini", "kling"):
        prompt, note = _build_video_prompt(
            mode="avatar",
            provider=provider,
            prompt=user,
            has_identity_image=True,
            has_continue=True,
            generate_audio=True,
            duration_seconds=6,
            voice="ara",
        )
        lower = prompt.lower()
        assert note is not None and "continuing" in note.lower(), provider
        assert "identity" in lower, provider
        assert "bathroom mirror" in lower, provider
        assert "under-eye cream" in lower or "under eye cream" in lower, provider
        # Quoted dialogue, not a raw "says:" marker that models may misread.
        assert 'says:' not in lower, provider
        assert "white tank top" in lower, provider
        # Scene description is not the spoken line.
        assert '"Bathroom mirror' not in prompt, provider


def test_quoted_says_line_keeps_trailing_stage_direction_as_scene() -> None:
    """Regression: text after a quoted line is direction, not dialogue to read out."""
    spoken, scene = split_avatar_user_prompt(
        'Kitchen island, soft light. She says: "free shipping this week." '
        "Then the camera pushes in and she lifts the box."
    )
    assert spoken == "free shipping this week."
    assert "Kitchen island" in scene
    assert "camera pushes in" in scene
    assert "lifts the box" in scene


def test_unquoted_says_line_still_takes_the_whole_tail() -> None:
    """The documented UI form has no quotes; multi-sentence lines must survive."""
    spoken, scene = split_avatar_user_prompt(
        "Desk, soft light. She says: free shipping this week. Order before midnight."
    )
    assert spoken == "free shipping this week. Order before midnight."
    assert scene == "Desk, soft light"


def test_mid_line_quote_is_emphasis_not_a_line_boundary() -> None:
    """Only a quote opening the line bounds it; inner quotes stay in the line."""
    spoken, scene = split_avatar_user_prompt(
        'Desk, soft light. She says: I call it "the fix" for tired eyes.'
    )
    assert spoken == 'I call it "the fix" for tired eyes.'
    assert scene == "Desk, soft light"


def test_domains_expand_in_speech_but_not_in_visual_direction() -> None:
    """A URL on screen stays literal; a spoken one is expanded for TTS."""
    visual, _note = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt="Close-up of a laptop showing example.com in the browser.",
        has_identity_image=False,
        has_continue=False,
        generate_audio=True,
        duration_seconds=6,
    )
    assert "example.com" in visual
    assert "example dot com" not in visual

    spoken_scene, _note = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt='Founder at a desk says "check out example.com today" to camera.',
        has_identity_image=False,
        has_continue=False,
        generate_audio=True,
        duration_seconds=6,
    )
    assert "example dot com" in spoken_scene

    talking, _note = _build_video_prompt(
        mode="avatar",
        provider="gemini",
        prompt="Desk, soft light. She says: visit example.com now.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=8,
        voice="ara",
    )
    assert "example dot com" in talking


def test_orientation_follows_requested_aspect_ratio() -> None:
    """Regression: the frame was described as vertical whatever the user picked."""
    for aspect, word in (("9:16", "vertical"), ("1:1", "square"), ("3:4", "vertical")):
        prompt, _note = _build_video_prompt(
            mode="avatar",
            provider="gemini",
            prompt="Desk, soft light. She says: hello there.",
            has_identity_image=True,
            has_continue=False,
            generate_audio=True,
            duration_seconds=8,
            voice="ara",
            aspect_ratio=aspect,
        )
        assert f"Short {word} clip." in prompt, aspect


def test_video_continue_keeps_full_prompt() -> None:
    """Plain video continue still uses the full user text as direction."""
    prompt, _note = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt="Slow pan across a rainy street at night.",
        has_identity_image=False,
        has_continue=True,
        generate_audio=True,
        duration_seconds=6,
    )
    assert "Slow pan across a rainy street" in prompt
    assert "Continue this video seamlessly" in prompt
