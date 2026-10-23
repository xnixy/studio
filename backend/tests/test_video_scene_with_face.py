"""Video mode may carry a face so a scene can hold more than one person.

Talking locks the cast to a single subject and a single speaker, which is right for a
monologue and blocks a street interview. Video mode keeps the likeness but leaves the
cast and the dialogue open.
"""
from app.routers.play_video_helpers import _build_video_prompt

INTERVIEW = (
    "Two people on a Manhattan sidewalk at night. A reporter walks up with a mic and "
    'asks "what brings you out here?" She laughs and says "just testing what Studio can do."'
)


def build(prompt: str, *, face: bool, audio: bool = True, provider: str = "seedance"):
    return _build_video_prompt(
        mode="video", provider=provider, prompt=prompt,
        has_identity_image=face, has_continue=False,
        generate_audio=audio, duration_seconds=12,
    )[0]


def test_cafe_question_is_asked_before_the_friend_replies():
    prompt = (
        "She's at a cafe table, talking to a friend. "
        'The friend replies "I didn\'t know, that\'s so cool." '
        '"Do you know you can clone your own voice and reuse it?"'
    )
    text = build(prompt, face=True)
    assert text.index("clone your own voice") < text.index("friend replies")


def test_two_hander_does_not_give_both_speakers_the_standin():
    text = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt='Cafe. She says "I got the job." He says "I knew you would."',
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        voice="ara",
    )[0]
    assert "person in the face photo uses the voice from <AUDIO_0>" in text
    assert "Spoken words use the voice from <AUDIO_0>" not in text
    assert "A reporter walks up with a mic" in build(INTERVIEW, face=True)


def test_face_locks_likeness_without_locking_the_cast():
    text = build(INTERVIEW, face=True)
    assert "IDENTITY (highest priority):" in text
    # Talking's single-subject rule would forbid the reporter.
    assert "only subject" not in text
    assert "Other people may appear" in text


def test_other_characters_must_not_inherit_the_reference_face():
    assert "never take the @Image1 face" in build(INTERVIEW, face=True)


def test_ambiguous_pronoun_falls_back_to_whoever_was_already_there():
    # "A reporter walks up ... she says" reads as the reporter speaking, so the scene
    # needs an explicit tie-break or the face lands on the wrong character.
    text = build(INTERVIEW, face=True)
    assert "already in frame when the shot opens" in text
    assert "never the one who walks up" in text


def test_scene_wardrobe_keeps_a_friends_outfit_on_the_friend():
    text = build(
        'Cafe. Her friend in a red dress. She wears a gray tee and says "I got the job."',
        face=True,
    ).lower()
    assert "friend's outfit stays on the friend" in text
    assert "not the selected face" in text
    text = build(INTERVIEW, face=True)
    assert "DIALOGUE:" in text
    assert "take turns" in text
    assert "quoted words are spoken exactly" in text.lower()


def test_quoted_dialogue_does_not_add_camera_eyeline():
    # A sidewalk ask used to pick up "spoken out loud on camera" and both
    # speakers faced the lens. Eyeline follows who they are talking to.
    text = build(INTERVIEW, face=True).lower()
    assert "spoken out loud on camera" not in text
    assert "looks at the person they are talking to" in text
    assert "keep that person in the shot" in text
    assert "presenter talking to the viewer" in text


def test_scene_without_quotes_gets_no_dialogue_block():
    assert "DIALOGUE:" not in build("Slow pan over a rainy street", face=True)


def test_contractions_are_not_mistaken_for_dialogue():
    # Two apostrophes in one sentence is ordinary prose, not a spoken line.
    text = build("A woman walks down the street, she's carrying a bag, it's raining", face=True)
    assert "DIALOGUE:" not in text


def test_curly_quotes_still_count_as_dialogue():
    assert "DIALOGUE:" in build("She turns and says “what brings you out here?”", face=True)


def test_silent_scene_gets_no_dialogue_block():
    text = build(INTERVIEW, face=True, audio=False)
    assert "DIALOGUE:" not in text
    assert "PICTURE ONLY" in text
    assert "Do not speak" in text


def test_no_stray_period_after_a_closing_quote():
    assert '."\n' in build(INTERVIEW, face=True) or build(INTERVIEW, face=True).endswith('."')
    assert '.".' not in build(INTERVIEW, face=True)


def test_grok_scene_with_face_uses_image_tag():
    text = build(INTERVIEW, face=True, provider="xai")
    assert "<IMAGE_1>" in text
    assert "the first reference image" not in text


def test_grok_quoted_scene_binds_voice_tag():
    text = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt=INTERVIEW,
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=15,
        voice="ara",
    )[0]
    assert "<AUDIO_0>" in text


def test_grok_silent_scene_does_not_force_speech():
    text = _build_video_prompt(
        mode="video",
        provider="xai",
        prompt="Slow pan over a rainy street",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=15,
        voice="ara",
    )[0]
    assert "<IMAGE_1>" in text
    assert "<AUDIO_0>" not in text


def test_plain_scene_without_a_face_has_no_identity_block():
    text = build("Slow pan over a rainy street", face=False)
    assert "IDENTITY:" not in text
    assert text.startswith("FOCUS")
    assert "Slow pan over a rainy street." in text


def test_video_clip_defaults_to_deep_focus():
    text = build("Two friends at a cafe", face=True).lower()
    assert "deep focus" in text
    assert "blurred background" in text


def test_seedance_scene_tts_does_not_ask_to_respeak_quotes() -> None:
    text = _build_video_prompt(
        mode="video",
        provider="seedance",
        prompt='Cafe. She says "I got the job." He says "I knew you would."',
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=12,
        voice_audio_speakers=["face", "other"],
    )[0].lower()
    assert "voices and words come from the attached audio" in text
    assert "quoted words are spoken exactly" not in text
    assert "@audio1 defines the voice" in text
    assert "@audio2 defines the voice" in text


def test_talking_mode_makes_the_face_the_speaker() -> None:
    """Talking is one person saying one line. A friend in frame is a listener.

    The old default-speaker wording let Grok treat "talking to a friend" as a
    two-hander, invent a new lead in the named clothes, and seat the Face as
    the friend. True two-handers belong in Video.
    """
    kitchen = _build_video_prompt(
        mode="avatar", provider="seedance", prompt="Kitchen. says: hello there",
        has_identity_image=True, has_continue=False, generate_audio=True,
        duration_seconds=6,
    )[0]
    assert "@Image1 says the spoken line" in kitchen
    assert "only foreground person" in kitchen
    assert "a friend is the listener" not in kitchen
    assert "Only the person from @Image1 speaks" not in kitchen
    assert "@Image1 is the default speaker" not in kitchen
    cafe = _build_video_prompt(
        mode="avatar",
        provider="seedance",
        prompt="Kitchen, talking to a friend. says: hello there",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=6,
    )[0]
    assert "@Image1 says the spoken line" in cafe
    assert "does not say this line" in cafe
    assert "a friend is the listener" in cafe.lower()


def test_unquoted_speech_still_names_a_speaker():
    """The reported bug: "talk about X" with two people gave the line to the wrong face.

    Quotes alone gated the dialogue rules, so an unquoted ask produced a prompt with
    no speaker named at all and the model picked whoever it liked.
    """
    text = build(
        "A woman at a cafe, her friend sits across from her, talk about the new drop",
        face=True,
    )
    assert "@Image1 is the default speaker" in text
    assert "DIALOGUE:" in text


def test_second_speaker_is_still_allowed():
    """A written line for another character must survive the default-speaker rule."""
    text = build(INTERVIEW, face=True)
    assert "speak only the lines the text gives them" in text


def test_speaker_rule_uses_each_providers_own_tag():
    for provider, tag in (
        ("xai", "<IMAGE_1>"),
        ("seedance", "@Image1"),
        ("gemini", "the reference face image"),
        ("kling", "the input image"),
    ):
        text = build("Two friends at a cafe, talk about the drop", face=True, provider=provider)
        assert f"{tag} is the default speaker" in text


def test_signage_is_not_staged_as_dialogue():
    """"A sign that says OPEN" is written text, not someone talking.

    Broadening speech detection past quotation marks made bare "says" fire, which
    staged a conversation for a storefront and risked the sign being read aloud.
    """
    assert "DIALOGUE:" not in build("A storefront with a sign that says OPEN", face=True)
    assert "DIALOGUE:" not in build("A poster reading SALE on a brick wall", face=True)
    # A real line alongside signage must still count.
    assert "DIALOGUE:" in build("A sign that says OPEN, then she says hello", face=True)


def test_first_reference_is_described_when_there_is_no_face():
    """Image 1 is only skipped because IDENTITY describes the face.

    Without a face nothing described it, so a Video clip carrying two product shots
    shipped its first reference as unexplained pixels.
    """
    text = _build_video_prompt(
        mode="video", provider="xai", prompt="Two products on a table",
        has_identity_image=False, has_continue=False, generate_audio=True,
        image_roles=["reference", "product"],
    )[0]
    assert "<IMAGE_1>:" in text
    assert "<IMAGE_2>:" in text


def test_face_reference_is_not_repeated_in_the_manifest():
    text = build("Two friends at a cafe", face=True, provider="xai")
    assert "<IMAGE_1>:" not in text


def test_line_longer_than_the_clip_warns_instead_of_cutting_silently():
    """A written line over budget used to be clamped with no warning at all.

    The render simply stopped mid-word. The improvised branch has a word budget;
    a user-written line had nothing, so say what will happen and what to cut.
    """
    note = _build_video_prompt(
        mode="avatar", provider="xai",
        prompt="Kitchen. says: " + " ".join(["word"] * 90),
        has_identity_image=True, has_continue=False, generate_audio=True,
        duration_seconds=15,
    )[1]
    assert "will cut off" in note
    assert "33 words" in note


def test_line_that_fits_gets_no_length_warning():
    note = _build_video_prompt(
        mode="avatar", provider="xai", prompt="Kitchen. says: hello there friend",
        has_identity_image=True, has_continue=False, generate_audio=True,
        duration_seconds=15,
    )[1]
    assert "cut off" not in (note or "")
