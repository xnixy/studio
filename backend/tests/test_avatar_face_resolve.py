"""Avatar face resolution must deliver identity for every provider family."""
from app.routers.play_video_helpers import (
    _avatar_identity_rules,
    _avatar_look_rules,
    _build_video_prompt,
)


def test_identity_rules_forbid_new_person() -> None:
    text = _avatar_identity_rules(image_tag="@Image1").lower()
    assert "identity (highest priority)" in text
    assert "different person" in text or "do not invent" in text
    assert "treat @image1 as the identity ground truth" in text
    assert "makeup" in text
    assert "finish" in text
    assert "de-filter" in text
    assert "unless the scene text asks" in text


def test_look_rules_are_real_life_not_scene_specific() -> None:
    text = _avatar_look_rules().lower()
    assert "ultra-real" in text
    assert "photoreal" in text
    assert "cgi" in text
    # Photoreal is the default, not a ban: a scene that asks for another style has
    # to be able to win, or a stylized talking head is unreachable at any prompt.
    assert "default" in text
    assert "scene text" in text
    # House look only. No place, body-part, or sample-prompt details.
    for banned in ("neck", "crosswalk", "city", "street", "strangers", "overcast", "kitchen"):
        assert banned not in text, banned


def test_all_providers_get_identity_lock_in_avatar_prompt() -> None:
    for provider in ("xai", "seedance", "gemini", "kling"):
        prompt, note = _build_video_prompt(
            mode="avatar",
            provider=provider,
            prompt="Kitchen, black tee. She says: hello free shipping.",
            has_identity_image=True,
            has_continue=False,
            generate_audio=True,
            duration_seconds=5,
            voice="ara",
        )
        lower = prompt.lower()
        assert "identity" in lower, provider
        assert "hello free shipping" in lower or "free shipping" in lower, provider
        assert "real-life" in lower or "photoreal" in lower, provider
        assert note is not None
        # Scene place still comes only from the user prompt.
        assert "kitchen" in lower, provider
        assert "crosswalk" not in lower, provider
