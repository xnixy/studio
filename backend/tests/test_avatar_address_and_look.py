"""Eyeline and house look for Talking clips.

Three artifacts drove these: a speaker who opened on the camera and swung to her
listener mid-sentence, a speaker who asked the person beside her and still turned
to the lens, and a clip that opened as a handheld selfie vlog when the scene
text asked for nothing of the kind.
"""
from app.routers.play_prompt_cast import avatar_frame_rule
from app.routers.play_video_helpers import (
    _audio_tail,
    _avatar_address_rule,
    _avatar_look_rules,
    _build_video_prompt,
    _scene_has_addressee,
    _seedance_drive_audio,
)


def _avatar_prompt(
    provider: str,
    prompt: str,
    *,
    has_identity_image: bool = True,
    voice: str | None = None,
    generate_audio: bool = True,
) -> str:
    text, _note = _build_video_prompt(
        mode="avatar",
        provider=provider,
        prompt=prompt,
        has_identity_image=has_identity_image,
        has_continue=False,
        voice=voice,
        generate_audio=generate_audio,
    )
    return text


def test_look_rules_do_not_impose_a_shooting_format() -> None:
    # The SCENE block owns camera language. A house look that also prescribes the
    # format overrides scene text the user did write. "On camera" was meant as
    # live-action and was read as look-at-lens, so it stays out of LOOK.
    text = _avatar_look_rules().lower()
    assert "photoreal" in text
    for banned in (
        "phone-video",
        "phone video",
        "selfie",
        "vlog",
        "handheld",
        "ugc",
        "on camera",
        "eyeline",
        "look at",
    ):
        assert banned not in text, banned


def test_address_rule_binds_eyeline_before_the_first_frame() -> None:
    text = _avatar_address_rule("talking to a friend across the table").lower()
    assert "eyeline" in text
    # Both swings are the bug: camera to listener, and listener back to camera.
    assert "never switch eyeline mid-line" in text
    assert "turn to the camera while speaking" in text


def test_address_rule_turns_toward_a_friend_beside_her() -> None:
    # Angled camera + friend beside her: models looked 'front' down the table.
    text = _avatar_address_rule("she asks the person beside her").lower()
    assert "sit beside" in text or "sits beside" in text
    assert "straight ahead" in text
    assert "camera may sit off to the side" in text
    # "The person beside her" is who they are speaking to. Requiring a proper
    # name sent those scenes to the lens.
    assert "beside" in text
    assert "named" not in text
    # Solo copy must not leak into a conversation ADDRESS.
    assert "do not invent a friend" not in text


def test_talking_prompt_carries_the_address_rule() -> None:
    for provider in ("xai", "seedance", "gemini", "kling"):
        text = _avatar_prompt(
            provider, "Cafe table, she asks her friend across the table. She says: are you free Friday?"
        ).lower()
        assert "address:" in text, provider
        assert "eyeline" in text, provider


def test_faceless_talking_prompt_carries_the_address_rule() -> None:
    for provider in ("xai", "gemini"):
        text = _avatar_prompt(
            provider,
            "Cafe table, she asks her friend. She says: are you free Friday?",
            has_identity_image=False,
        ).lower()
        assert "eyeline" in text, provider


def test_delivery_guidance_describes_tone_without_an_addressee() -> None:
    # Delivery sets how it sounds. Who it is aimed at is ADDRESS's call, and the
    # old "talks to a friend on camera" phrasing quietly voted for the lens.
    text = _audio_tail(generate_audio=True, talking=True, provider="xai").lower()
    assert "relaxed natural speech" in text
    assert "on camera" not in text


def test_look_does_not_set_eyeline() -> None:
    # ADDRESS is the only house rule that may mention the lens. LOOK used to
    # say "on camera" and conversation scenes still faced the viewer.
    assert "camera" not in _avatar_look_rules().lower()
    assert "eyeline" not in _avatar_look_rules().lower()


def test_frame_rule_does_not_prescribe_a_shooting_format() -> None:
    # One NYC overhead clip is not a house camera. Prompts vary: drone, table-down,
    # wide walk, full figure. FRAME only forbids inventing what the scene omitted.
    text = avatar_frame_rule().lower()
    assert "do not invent" in text
    assert "scene" in text
    for banned in (
        "eye-level",
        "fisheye",
        "from above",
        "talking-head",
        "on camera",
        "3/4",
        "selfie",
        "vlog",
        "handheld",
    ):
        assert banned not in text, banned
    assert "camera" not in _avatar_look_rules().lower()


def test_written_camera_in_the_scene_is_left_alone() -> None:
    # House must not vote eye-level against a prompt that already named a camera.
    text = _avatar_prompt(
        "seedance",
        "Drone view of the boardwalk, full figure. says: just testing the new update.",
    ).lower()
    assert "drone view" in text
    assert "full figure" in text
    assert "eye-level" not in text
    assert "fisheye" not in text
    assert "do not invent a camera" in text


def test_look_defaults_to_deep_focus() -> None:
    text = _avatar_look_rules().lower()
    assert "deep focus" in text
    assert "background all sharp" in text
    assert "blurred background" in text


def test_conversation_scene_does_not_inject_a_camera_look() -> None:
    for provider in ("xai", "seedance", "gemini", "kling"):
        text = _avatar_prompt(
            provider,
            "Cafe table, she asks the person beside her. She says: are you free Friday?",
        ).lower()
        assert "address:" in text, provider
        assert "turn to the camera while speaking" in text, provider
        assert "looking at camera" not in text, provider
        assert "talking-head" not in text, provider
        # Next to the line, not only in the ADDRESS block at the end.
        assert "speak this line to that person" in text, provider
        assert "keep them in the shot" in text, provider
        assert "not straight ahead" in text, provider
        assert "turn her head" in text, provider
        assert "visible in the shot" in text, provider


def test_cafe_talking_keeps_the_face_as_speaker_in_the_named_outfit() -> None:
    # "yellow top" used to miss the clothes detector, so Grok invented a new
    # woman in yellow and seated the Face as the friend who listens.
    text = _avatar_prompt(
        "xai",
        "She's at a cafe table in a yellow top, talking to a friend across from her. "
        "says: I got the job. I still can't believe I said yes.",
    ).lower()
    assert "<image_1> says the spoken line" in text
    assert "listener" in text
    assert "this scene names clothes" in text
    assert "unnamed clothes go on the selected face" in text
    assert "yellow top" in text
    assert "wear the clothes the scene names" in text
    assert "not the outfit in the photo" in text
    assert "take the photo clothes off" not in text
    assert "friend's outfit stays on the friend" in text
    assert "speak this line to that person" in text
    assert "keep them in the shot" in text
    assert "not straight ahead" in text
    assert "i got the job" in text
    assert "look at the person they are talking to" in text
    assert "not past them" in text
    assert "3/4" not in text
    assert "portrait blur" not in text


def test_sync_picture_pass_does_not_ask_grok_to_speak() -> None:
    text = _avatar_prompt(
        "xai",
        "She's at a cafe table in a yellow top, talking to a friend across from her. "
        "says: I got the job. I still can't believe I said yes.",
        generate_audio=False,
    ).lower()
    assert "picture only" in text
    assert "mouths at rest" in text
    assert "do not speak" in text
    assert "no one speaks on this pass" in text
    assert "speaks this line" not in text
    assert "lips locked to the words" not in text
    assert "<audio_0>" not in text
    assert "yellow top" in text
    assert "look at that person" in text


XAI_VIDEO_PROMPT_MAX = 4096
# Cafe clip is ~200 user chars. House must leave ~1800 for a long scene + line.
# FRAME joined LOOK/ADDRESS after the NYC overhead clip, so this is not 2000.
GROK_HOUSE_BUDGET = 2500


def test_grok_talking_prompt_fits_xai_length_limit() -> None:
    # House LOOK/ADDRESS/IDENTITY stacked past 4096 and Grok 400'd the cafe clip.
    cafe = (
        "She's at a cafe table in a yellow top, talking to a friend across from her. "
        "They look at the person they are talking to, not past them and not at the camera. "
        "says: I got the job. I still can't believe I said yes."
    )
    text = _avatar_prompt("xai", cafe, voice="jessica")
    assert len(text) < XAI_VIDEO_PROMPT_MAX, len(text)
    assert len(text) < GROK_HOUSE_BUDGET + len(cafe), len(text)


def test_grok_talking_prompt_fits_a_long_user_scene() -> None:
    # A real scene plus a 15s line is far longer than the cafe clip. House
    # overhead used to eat the 4096 cap before the user text got a turn.
    scene = (
        "She's at a cafe table in a yellow top, talking to a friend across from her. "
        "Late afternoon light, busy street outside, cups and a small pastry plate. "
    ) * 8
    line = " ".join(["I got the job and I still cannot believe I said yes to moving."] * 6)
    text = _avatar_prompt("xai", f"{scene} says: {line}", voice="jessica")
    assert len(scene) + len(line) > 1200
    assert len(text) < XAI_VIDEO_PROMPT_MAX, len(text)


def test_scene_only_prompt_does_not_hardcode_camera_address() -> None:
    # No "says:" means the model improvises the line. It should still take the
    # addressee from the scene rather than being told to face the lens.
    text = _avatar_prompt("xai", "Cafe table, she asks her friend across the table about Friday").lower()
    assert "talks to camera" not in text
    assert "eyeline" in text
    assert "talking-head" not in text


def test_solo_presenter_still_defaults_to_the_camera() -> None:
    text = _avatar_address_rule("Desk, soft window light, black hoodie").lower()
    assert "speak to the camera the whole line" in text
    assert "do not invent a friend" in text
    built = _avatar_prompt(
        "xai", "Desk, soft window light, black hoodie. He says: free shipping this week only."
    ).lower()
    assert "speak to the camera the whole line" in built
    assert "cast:" in built
    assert "only foreground person" in built
    assert "a friend is the listener" not in built
    assert "looking at camera" not in built
    assert "speak this line to that person" not in built
    assert "keep them in the shot" not in built


def test_faceless_conversation_is_not_forced_into_a_talking_head() -> None:
    text = _avatar_prompt(
        "xai",
        "Cafe table, she asks the person beside her. She says: are you free Friday?",
        has_identity_image=False,
    ).lower()
    assert "talking-head" not in text
    assert "turn to the camera while speaking" in text


def test_video_conversation_scene_gets_the_look_sentence() -> None:
    text, _note = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt='Two friends at a cafe. She says "I got the job." He says "I knew you would."',
        has_identity_image=False,
        has_continue=False,
    )
    lower = text.lower()
    assert "look at the person they are talking to" in lower
    assert "not past them" in lower
    assert "3/4" not in lower


NYC_SOLO = (
    "Shes standing in the streets of New York, dressed in yoga black pants "
    "casual white sneakers. says: Just testing the new update."
)


def test_nyc_solo_talking_does_not_name_a_friend() -> None:
    # The live clip invented a grey-hoodie extra because SPEAKER always said
    # "a friend is the listener" and ADDRESS was listener-first.
    for provider in ("xai", "seedance", "gemini", "kling"):
        text = _avatar_prompt(provider, NYC_SOLO).lower()
        assert "a friend is the listener" not in text, provider
        assert "speak this line to that person" not in text, provider
        assert "speak to the camera the whole line" in text, provider
        assert "cast:" in text, provider
        assert "interview shoulder" in text, provider
        assert "place may show" not in text, provider
        assert "do not pull back" not in text, provider
        assert "frame:" in text, provider
        assert "do not invent a camera" in text, provider
        assert "shot at eye level" in text, provider
        assert "face large in the frame" in text, provider
        assert "just testing the new update" in text, provider
        assert "yoga black pants" in text, provider
        assert "do not complete a matching set from the photo" in text, provider


def test_talking_to_the_camera_is_solo_not_a_listener() -> None:
    assert not _scene_has_addressee("standing on a sidewalk talking to the camera")
    assert not _scene_has_addressee("she talks to the viewer about the drop")
    assert not _scene_has_addressee("streets of New York")
    assert not _scene_has_addressee("busy sidewalk, yellow cabs")
    assert _scene_has_addressee("talking to a friend across from her")
    text = _avatar_prompt(
        "seedance",
        "Sidewalk, black hoodie, talking to the camera. says: just a quick update.",
    ).lower()
    assert "a friend is the listener" not in text
    assert "speak this line to that person" not in text
    assert "cast:" in text


def test_seedance_audio_locks_mouths_from_frame_one() -> None:
    text = _seedance_drive_audio(["face"]).lower()
    assert "from the first frame" in text
    assert "do not delay the first word" in text
    assert "@audio1 defines the voice and the spoken words of the person in @image1" in text
    assert "both the words and the voice come from @audio1" in text
    assert "do not invent a different voice" in text


def test_seedance_friend_audio_is_not_the_face() -> None:
    text = _seedance_drive_audio(["face", "other"]).lower()
    assert "@audio2 defines the voice and the spoken words of the friend" in text
    assert "not the person in @image1" in text


def test_seedance_tts_drive_does_not_requote_the_line() -> None:
    """House TTS is the take. Quoting the line again made Seedance invent a voice."""
    text, _note = _build_video_prompt(
        mode="avatar",
        provider="seedance",
        prompt="Kitchen, black tee. says: just testing the new update.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=6,
        voice_audio_speakers=["face"],
    )
    lower = text.lower()
    assert "@audio1 defines the voice" in lower
    assert "both the words and the voice come from @audio1" in lower
    assert "speaks this line" not in lower
    assert "just testing the new update" not in lower
    assert "pace the full line" not in lower
    assert "mouths follow the attached audio" in lower
    assert "kitchen" in lower
    assert "black tee" in lower


def test_seedance_tts_drive_keeps_listener_without_requoting() -> None:
    text, _note = _build_video_prompt(
        mode="avatar",
        provider="seedance",
        prompt="She's at a cafe table, talking to a friend across from her. says: I got the job.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=6,
        voice_audio_speakers=["face"],
    )
    lower = text.lower()
    assert "a friend is the listener" in lower
    assert "address that person" in lower
    assert "speak this line to that person" not in lower
    assert "i got the job" not in lower
    assert "mouths follow the attached audio" in lower


def test_cafe_talking_still_names_the_friend_as_listener() -> None:
    text = _avatar_prompt(
        "seedance",
        "She's at a cafe table in a yellow top, talking to a friend across from her. "
        "says: I got the job.",
    ).lower()
    assert "a friend is the listener" in text
    assert "speak this line to that person" in text
    assert "cast:" not in text
    assert "do not invent a friend" not in text
    assert "look at the person they are talking to" in text
    assert "frame:" in text
    assert "shot at eye level" in text
    assert "face large in the frame" in text
