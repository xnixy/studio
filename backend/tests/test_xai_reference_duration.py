"""Grok 1.5 allows 15s with or without a face. The old v1 10s cap is gone."""
from app.play_models import get_play_model
from app.routers.play_video_helpers import clamp_duration_for_provider
from app.xai_media import build_xai_video_payload


def test_reference_video_keeps_fifteen() -> None:
    assert clamp_duration_for_provider(15, provider="xai", has_reference_images=True) == 15


def test_text_to_video_keeps_fifteen() -> None:
    assert clamp_duration_for_provider(15, provider="xai", has_reference_images=False) == 15


def test_short_reference_video_untouched() -> None:
    assert clamp_duration_for_provider(6, provider="xai", has_reference_images=True) == 6


def test_retired_clip_engines_are_off_the_catalog() -> None:
    from app.play_models import PLAY_MODELS

    ids = {m.id for m in PLAY_MODELS}
    assert "xai-video" not in ids
    assert "xai-avatar-video" not in ids
    assert "kling-v3" not in ids
    assert "veo-3.1" not in ids
    assert "sync-lipsync" not in ids


def test_other_providers_still_honor_their_own_ceilings() -> None:
    assert clamp_duration_for_provider(15, provider="seedance", has_reference_images=True) == 15
    assert clamp_duration_for_provider(
        30, provider="seedance", model_id="seedance-2-5", max_duration=30
    ) == 30
    assert clamp_duration_for_provider(
        30, provider="seedance", model_id="seedance-2-5", max_duration=15
    ) == 15


def test_grok_image_catalog_uses_imagine_2() -> None:
    stills = get_play_model("xai-image-quality", "image")
    assert stills.provider_model == "grok-imagine-image-2.0"


def test_seedance_25_is_in_catalog() -> None:
    video = get_play_model("seedance-2-5", "video")
    avatar = get_play_model("seedance-avatar", "avatar")
    assert video.provider_model == "seedance-2-5"
    assert video.max_duration_seconds == 30
    assert avatar.provider_model == "seedance-2-5"
    assert avatar.max_duration_seconds == 30


def test_payload_sends_reference_images_and_voice() -> None:
    payload = build_xai_video_payload(
        model="grok-imagine-video-1.5",
        prompt="The person from <IMAGE_1> speaks with the voice from <AUDIO_0>.",
        duration=15,
        aspect_ratio="9:16",
        resolution="720p",
        reference_image_urls=["data:image/jpeg;base64,abc"],
        reference_audio_voice_ids=["eve"],
    )
    assert payload["model"] == "grok-imagine-video-1.5"
    assert payload["duration"] == 15
    assert payload["reference_images"] == [{"url": "data:image/jpeg;base64,abc"}]
    assert payload["reference_audios"] == [{"voice_id": "eve"}]
    assert "image" not in payload


def test_payload_voice_only_without_images() -> None:
    payload = build_xai_video_payload(
        model="grok-imagine-video-1.5",
        prompt="A rainy street.",
        duration=8,
        aspect_ratio="16:9",
        resolution="720p",
        reference_audio_voice_ids=["ara"],
    )
    assert payload["reference_audios"] == [{"voice_id": "ara"}]
    assert "reference_images" not in payload
