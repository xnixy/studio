"""Hidden Talking clip still: Face + scene, no house camera."""
from app.play_pricing import compute_play_quote
from app.routers.play_clip_still import clip_still_prompt
from app.routers.play_video_helpers import split_avatar_user_prompt


def test_old_photo_quote_is_clip_credits() -> None:
    quote = compute_play_quote(mode="lipsync", model_id="seedance-photo-fast")
    assert quote.breakdown.get("still_tokens") is None
    assert quote.meter == "play_avatar"
    assert quote.total == quote.per_item


def test_talking_credits_follow_length() -> None:
    short = compute_play_quote(mode="avatar", model_id="seedance-avatar-fast", duration_seconds=5)
    longer = compute_play_quote(
        mode="avatar", model_id="seedance-avatar-fast", duration_seconds=15
    )
    hi = compute_play_quote(
        mode="avatar",
        model_id="seedance-avatar-fast",
        duration_seconds=5,
        resolution="4k",
    )
    assert short.per_item == 8
    assert longer.per_item > short.per_item
    assert hi.per_item > short.per_item


def test_clip_still_prompt_follows_the_scene() -> None:
    text = clip_still_prompt(scene="NYC streets, yoga black pants, drone shot from above")
    assert "NYC streets" in text
    assert "yoga black pants" in text
    assert "drone shot from above" in text
    lower = text.lower()
    assert "eye-level" not in lower
    assert "fisheye" not in lower
    assert "3/4" not in lower
    assert "talking-head" not in lower
    assert "waist-up" not in lower
    assert "says:" not in text
    assert "Mouth closed" in text


def test_clip_still_does_not_invent_a_camera() -> None:
    text = clip_still_prompt(scene="full figure walking, wide shot")
    assert "full figure walking" in text
    assert "wide shot" in text
    assert "Do not invent a camera" in text


def test_empty_scene_still_has_a_fallback_place() -> None:
    text = clip_still_prompt(scene="  ")
    assert "simple real-life setting" in text


def test_talking_tts_uses_the_spoken_line_only() -> None:
    spoken, scene = split_avatar_user_prompt("Kitchen island, black tee. says: free shipping")
    assert spoken == "free shipping"
    assert "Kitchen" in scene
    spoken_empty, _scene = split_avatar_user_prompt("Kitchen island, black tee. says:")
    assert spoken_empty == ""
    spoken_bare, scene_bare = split_avatar_user_prompt("Hey, welcome back")
    assert spoken_bare == "Hey, welcome back"
    assert scene_bare == ""
