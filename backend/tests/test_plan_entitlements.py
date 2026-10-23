"""Plan entitlements: Free = Seedance Fast (and Grok stills); Advanced needs Starter+."""
from app.plan_entitlements import (
    CODE_ADVANCED_REQUIRED,
    model_lane,
    plan_allows_model,
    plan_entitlements,
    raise_if_model_not_allowed,
)
from app.play_models import get_play_model
from fastapi import HTTPException


def test_free_allows_seedance_fast_blocks_25() -> None:
    fast = get_play_model("seedance-2-0-fast", "video")
    flagship = get_play_model("seedance-2-5", "video")
    assert model_lane(fast) == "fast"
    assert model_lane(flagship) == "advanced"
    assert plan_allows_model("free", fast) is True
    assert plan_allows_model("free", flagship) is False
    assert plan_allows_model("starter", flagship) is True


def test_retired_photo_models_alias_to_talking() -> None:
    photo = get_play_model("seedance-photo-fast", "lipsync")
    assert photo.id == "seedance-avatar-fast"
    assert model_lane(photo) == "fast"
    assert plan_allows_model("free", photo) is True
    adv = get_play_model("seedance-photo", "lipsync")
    assert adv.id == "seedance-avatar"
    assert model_lane(adv) == "advanced"


def test_raise_advanced_has_code() -> None:
    seedance = get_play_model("seedance-avatar", "avatar")
    try:
        raise_if_model_not_allowed("free", seedance)
        raise AssertionError("expected HTTPException")
    except HTTPException as exc:
        assert exc.status_code == 403
        assert isinstance(exc.detail, dict)
        assert exc.detail.get("code") == CODE_ADVANCED_REQUIRED


def test_entitlements_public_shape() -> None:
    free = plan_entitlements("free")
    assert free.advanced_models is False
    assert "avatar" in free.modes
    assert "lipsync" not in free.modes
    paid = plan_entitlements("starter")
    assert paid.advanced_models is True


def test_catalog_marks_locked_for_free() -> None:
    from app.play_models import catalog_public

    rows = catalog_public(plan_name="free")
    by_id = {r["id"]: r for r in rows}
    assert by_id["seedance-2-0-fast"]["lane"] == "fast"
    assert by_id["seedance-2-0-fast"]["locked"] is False
    assert by_id["seedance-2-5"]["lane"] == "advanced"
    assert by_id["seedance-2-5"]["locked"] is True
    assert "xai-video" not in by_id
    assert "kling-v3" not in by_id
    assert "veo-3.1" not in by_id


def test_catalog_face_reference_support() -> None:
    from app.play_models import catalog_public, get_play_model

    rows = catalog_public()
    by_id = {r["id"]: r for r in rows}
    assert by_id["seedance-2-0-fast"]["supports_face_reference"] is True
    assert by_id["seedance-2-5"]["supports_face_reference"] is True
    assert get_play_model("seedance-2-0-fast", "video").supports_face_reference is True


def test_clip_defaults_are_seedance_fast() -> None:
    assert get_play_model(None, "video").id == "seedance-2-0-fast"
    assert get_play_model(None, "avatar").id == "seedance-avatar-fast"
    assert get_play_model(None, "lipsync").id == "seedance-avatar-fast"
