"""Extend (continue) and multi-reference behaviour.

Extending has two distinct image roles that used to be collapsed into one list:
the prior clip's last frame (the literal opening frame) and a face plate (a
likeness reference). Providers treat those differently, so the split has to hold
from resolve through to the provider call.
"""
from app.routers.play_video_helpers import (
    PROVIDER_MAX_REF_IMAGES,
    _build_video_prompt,
    _reference_manifest,
)


def continue_prompt(provider: str, *, mode: str = "video", face: bool = True) -> str:
    return _build_video_prompt(
        mode=mode,
        provider=provider,
        prompt="She walks toward the storefront and looks back.",
        has_identity_image=face,
        has_continue=True,
        generate_audio=True,
        duration_seconds=8,
    )[0]


def test_extend_keeps_the_identity_lock_on_every_provider() -> None:
    """Regression: only Seedance named the attached face, so the other three
    shipped a face plate with nothing saying whose likeness it was."""
    for provider in ("gemini", "kling", "xai", "seedance"):
        text = continue_prompt(provider)
        lowered = text.lower()
        assert "identity" in lowered, provider
        assert "walks toward the storefront" in text, provider


def test_extend_without_a_face_stays_free_of_identity_rules() -> None:
    for provider in ("gemini", "kling", "xai"):
        text = continue_prompt(provider, face=False)
        assert "IDENTITY" not in text, provider


def test_talking_extend_still_splits_scene_and_line() -> None:
    text = _build_video_prompt(
        mode="avatar",
        provider="gemini",
        prompt='Bathroom mirror, white tank. She says: "switch today." Then she smiles.',
        has_identity_image=True,
        has_continue=True,
        generate_audio=True,
        duration_seconds=8,
        voice="ara",
    )[0]
    assert '"switch today."' in text
    assert "Then she smiles" in text
    # The trailing direction is scene, so it must not be inside the spoken line.
    assert '"switch today." Then she smiles' not in text


def test_reference_manifest_names_every_extra_image() -> None:
    """Regression: only the first image was ever mentioned, so a product shot or a
    second person attached as reference 2 arrived as unexplained pixels."""
    manifest = _reference_manifest(
        provider="seedance",
        image_roles=["identity", "her friend", "the product"],
    )
    assert "@Image2: her friend." in manifest
    assert "@Image3: the product." in manifest
    # The identity image is described by the identity block, not here.
    assert "@Image1" not in manifest


def test_reference_manifest_uses_ordinals_off_seedance() -> None:
    manifest = _reference_manifest(provider="gemini", image_roles=["identity", "her friend"])
    assert "reference image 2: her friend." in manifest
    assert "@Image" not in manifest


def test_reference_manifest_uses_xai_image_tags() -> None:
    manifest = _reference_manifest(provider="xai", image_roles=["identity", "her friend"])
    assert "<IMAGE_2>: her friend." in manifest
    assert "@Image" not in manifest


def test_reference_manifest_falls_back_when_no_role_given() -> None:
    manifest = _reference_manifest(provider="seedance", image_roles=["identity", "reference"])
    assert "@Image2" in manifest
    assert "supporting reference" in manifest


def test_reference_manifest_is_empty_without_extras() -> None:
    assert _reference_manifest(provider="seedance", image_roles=["identity"]) == ""
    assert _reference_manifest(provider="seedance", image_roles=[]) == ""


def test_manifest_reaches_the_video_prompt() -> None:
    text = _build_video_prompt(
        mode="video",
        provider="seedance",
        prompt="She hands the bottle to her friend at the counter.",
        has_identity_image=True,
        has_continue=False,
        generate_audio=True,
        duration_seconds=8,
        image_roles=["identity", "her friend", "the bottle"],
    )[0]
    assert "REFERENCES:" in text
    assert "@Image2: her friend." in text
    assert "@Image3: the bottle." in text


def test_kling_takes_a_single_reference_image() -> None:
    """Kling image2video accepts one image, so a second person from a reference
    is not possible there — the cap is what tells the user instead of a silent drop."""
    assert PROVIDER_MAX_REF_IMAGES["kling"] == 1
    assert PROVIDER_MAX_REF_IMAGES["gemini"] == 3
    assert PROVIDER_MAX_REF_IMAGES["seedance"] == 9
