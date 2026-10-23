"""Auto length from spoken line for Talking clips."""
from app.routers.play_video_helpers import (
    clamp_duration_for_provider,
    estimate_speech_seconds,
    split_avatar_user_prompt,
)


def test_estimate_uses_spoken_line_not_scene() -> None:
    prompt = (
        "Bright kitchen with a long description of plants and sunlight and props. "
        "She says: free shipping this week only."
    )
    spoken, scene = split_avatar_user_prompt(prompt)
    assert "kitchen" in scene.lower()
    assert "free shipping" in spoken.lower()
    sec = estimate_speech_seconds(prompt, mode="avatar")
    # Short spoken line should not be inflated by the long scene.
    assert 4 <= sec <= 10


def test_estimate_long_line_longer() -> None:
    short = estimate_speech_seconds("Kitchen. She says: hi.", mode="avatar")
    long = estimate_speech_seconds(
        "Kitchen. She says: free shipping this week only if you order before midnight "
        "and use the code in my bio for an extra ten percent off.",
        mode="avatar",
    )
    assert long >= short


def test_clamp_veo_snaps() -> None:
    assert clamp_duration_for_provider(5, provider="gemini") in {4, 6, 8}
    assert clamp_duration_for_provider(7, provider="gemini") in {4, 6, 8}
