"""Veo referenceImages are 8s-only on the Gemini API.

A Talking clip always attaches a face plate, and Auto sizes the clip to the spoken
line — so a short line asked Veo for 4s with referenceImages and came back as
400 INVALID_ARGUMENT "Your use case is currently not supported."
"""
import pytest

from app.gemini_video import VEO_REFERENCE_IMAGE_DURATION, normalize_veo_duration
from app.routers.play_video_helpers import clamp_duration_for_provider


@pytest.mark.parametrize("requested", [1, 4, 5, 6, 8, 15])
def test_reference_images_always_force_eight_seconds(requested: int) -> None:
    assert normalize_veo_duration(requested, has_reference_images=True) == 8


def test_plain_veo_still_snaps_to_four_six_eight() -> None:
    assert normalize_veo_duration(4) == 4
    assert normalize_veo_duration(5) == 6
    assert normalize_veo_duration(7) == 8


def test_talking_clip_is_planned_at_eight_not_the_spoken_length() -> None:
    # "Just testing what Studio can do." estimates ~4s; Veo cannot render that with a face.
    duration = clamp_duration_for_provider(
        4, provider="gemini", model_id="veo-3.1-generate-preview",
        max_duration=8, resolution="720p", has_reference_images=True,
    )
    assert duration == VEO_REFERENCE_IMAGE_DURATION


def test_veo_without_a_face_keeps_the_requested_length() -> None:
    duration = clamp_duration_for_provider(
        4, provider="gemini", model_id="veo-3.1-generate-preview",
        max_duration=8, resolution="720p", has_reference_images=False,
    )
    assert duration == 4


def test_other_providers_are_untouched_by_the_veo_rule() -> None:
    assert clamp_duration_for_provider(
        4, provider="seedance", max_duration=15, has_reference_images=True
    ) == 4
