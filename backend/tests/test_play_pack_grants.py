"""Unit tests: credit packs dual-write Play meters; legacy grants expand."""
from __future__ import annotations

from app.plans import (
    CREDIT_PACK_CATALOG,
    RETIRED_CREDIT_PACKS,
    apply_addons,
    apply_limit_grants,
    apply_limit_overrides,
    clip_credit_limit,
    credit_pack_for,
    plan_for,
    sale_credit_pack_for,
)
from app.workspace_access import limit_for_event


def test_clip_pool_sums_talking_and_scene() -> None:
    free = plan_for("free")
    starter = plan_for("starter")
    creator = plan_for("creator")
    studio = plan_for("studio")
    assert clip_credit_limit(free) == 25
    assert clip_credit_limit(starter) == 80
    assert clip_credit_limit(creator) == 200
    assert clip_credit_limit(studio) == 525
    assert limit_for_event(free, "play_avatar") == 25
    assert limit_for_event(free, "play_video") == 25
    assert limit_for_event(free, "video_generation") == 25
    assert limit_for_event(free, "play_still") == 12


def test_legacy_video_grant_expands_to_play_video_only() -> None:
    base = plan_for("starter")
    result = apply_limit_grants(base, {"video_credit_limit": 40})

    assert result.video_credit_limit == base.video_credit_limit + 40
    assert result.play_video_limit == base.play_video_limit + 40
    assert result.play_avatar_limit == base.play_avatar_limit
    assert clip_credit_limit(result) == clip_credit_limit(base) + 40
    assert result.play_still_limit == base.play_still_limit
    assert result.play_lipsync_limit == base.play_lipsync_limit


def test_legacy_image_grant_expands_still_and_face() -> None:
    base = plan_for("starter")
    result = apply_limit_grants(base, {"image_generation_limit": 90})

    assert result.image_generation_limit == base.image_generation_limit + 90
    assert result.play_still_limit == base.play_still_limit + 90
    assert result.play_face_limit == base.play_face_limit + 30  # 90 // 3


def test_legacy_lipsync_grant_expands_to_play_lipsync() -> None:
    base = plan_for("starter")
    result = apply_limit_grants(base, {"avatar_lipsync_limit": 20})

    assert result.avatar_lipsync_limit == base.avatar_lipsync_limit + 20
    assert result.play_lipsync_limit == base.play_lipsync_limit + 20


def test_dual_write_does_not_double_count() -> None:
    """When both legacy and play keys are present, apply each once only."""
    base = plan_for("starter")
    result = apply_limit_grants(
        base,
        {
            "video_credit_limit": 10,
            "play_video_limit": 10,
            "play_avatar_limit": 10,
        },
    )

    assert result.video_credit_limit == base.video_credit_limit + 10
    assert result.play_video_limit == base.play_video_limit + 10
    assert result.play_avatar_limit == base.play_avatar_limit + 10
    # Existing dual-written grants keep both sides (no one loses mid-month).
    assert clip_credit_limit(result) == clip_credit_limit(base) + 20


def test_video_10_pack_grants_clip_pool_once() -> None:
    base = plan_for("free")
    pack = credit_pack_for("video_10")
    assert pack is not None
    assert pack.grants["video_credit_limit"] == 50
    assert pack.grants["play_video_limit"] == 50
    assert "play_avatar_limit" not in pack.grants

    result = apply_limit_grants(base, pack.grants)
    assert result.video_credit_limit == base.video_credit_limit + 50
    assert result.play_video_limit == base.play_video_limit + 50
    assert result.play_avatar_limit == base.play_avatar_limit
    assert clip_credit_limit(result) == clip_credit_limit(base) + 50


def test_image_50_pack_grants_still_and_face() -> None:
    base = plan_for("free")
    pack = credit_pack_for("image_50")
    assert pack is not None
    assert pack.grants["image_generation_limit"] == 150
    assert pack.grants["play_still_limit"] == 150
    assert pack.grants["play_face_limit"] == 50

    result = apply_limit_grants(base, pack.grants)
    assert result.image_generation_limit == base.image_generation_limit + 150
    assert result.play_still_limit == base.play_still_limit + 150
    assert result.play_face_limit == base.play_face_limit + 50


def test_admin_override_legacy_keys_mirror_play_video_only() -> None:
    """Accounts tab sets video_credit_limit etc.; Clip pool sums play_*."""
    base = plan_for("free")
    result = apply_limit_overrides(
        base,
        {
            "video_credit_limit": 100,
            "image_generation_limit": 60,
            "avatar_lipsync_limit": 40,
        },
    )

    assert result.video_credit_limit == 100
    assert result.play_video_limit == 100
    assert result.play_avatar_limit == base.play_avatar_limit
    assert clip_credit_limit(result) == 100 + base.play_avatar_limit + 40
    assert result.image_generation_limit == 60
    assert result.play_still_limit == 60
    assert result.play_face_limit == 20  # 60 // 3
    assert result.avatar_lipsync_limit == 40
    assert result.play_lipsync_limit == 40


def test_admin_override_explicit_play_keys_not_overwritten() -> None:
    base = plan_for("free")
    result = apply_limit_overrides(
        base,
        {
            "video_credit_limit": 100,
            "play_video_limit": 55,
            "play_avatar_limit": 70,
        },
    )
    assert result.video_credit_limit == 100
    assert result.play_video_limit == 55
    assert result.play_avatar_limit == 70
    assert clip_credit_limit(result) == 125 + base.play_lipsync_limit


def test_lipsync_10_pack_grants_play_lipsync() -> None:
    base = plan_for("free")
    pack = credit_pack_for("lipsync_10")
    assert pack is not None
    assert pack.grants["avatar_lipsync_limit"] == 50
    assert pack.grants["play_lipsync_limit"] == 50

    result = apply_limit_grants(base, pack.grants)
    assert result.avatar_lipsync_limit == base.avatar_lipsync_limit + 50
    assert result.play_lipsync_limit == base.play_lipsync_limit + 50
    assert clip_credit_limit(result) == clip_credit_limit(base) + 50


def test_creator_burst_maps_clip_once() -> None:
    base = plan_for("starter")
    pack = credit_pack_for("creator_burst")
    assert pack is not None
    g = pack.grants
    assert g["video_credit_limit"] == g["play_video_limit"] == 25
    assert "play_avatar_limit" not in g
    assert g["image_generation_limit"] == g["play_still_limit"] == 45
    assert g["play_face_limit"] == 15
    assert g["avatar_lipsync_limit"] == g["play_lipsync_limit"] == 15

    result = apply_limit_grants(base, g)
    assert result.play_video_limit == base.play_video_limit + 25
    assert result.play_avatar_limit == base.play_avatar_limit
    assert clip_credit_limit(result) == clip_credit_limit(base) + 40
    assert result.play_still_limit == base.play_still_limit + 45
    assert result.play_face_limit == base.play_face_limit + 15
    assert result.play_lipsync_limit == base.play_lipsync_limit + 15
    assert result.voiceover_seconds_limit == base.voiceover_seconds_limit + 900


def test_video_addon_boosts_clip_pool_once() -> None:
    base = plan_for("starter")
    result = apply_addons(base, {"video_credits": 2})
    assert result.play_video_limit == base.play_video_limit + 10
    assert result.play_avatar_limit == base.play_avatar_limit
    assert clip_credit_limit(result) == clip_credit_limit(base) + 10


def test_voice_and_scripts_packs_unchanged() -> None:
    voice = credit_pack_for("voice_30m")
    scripts = credit_pack_for("scripts_25")
    assert voice is not None and scripts is not None
    assert voice.grants == {"voiceover_seconds_limit": 1_800}
    assert scripts.grants == {"script_generation_limit": 25}


def test_free_plan_image_aligned_with_play_still() -> None:
    free = plan_for("free")
    assert free.image_generation_limit == free.play_still_limit == 12


def test_credit_pack_user_copy_says_credits() -> None:
    banned = ("token", "grok", "veo", "lip-sync token")
    for pack in CREDIT_PACK_CATALOG:
        blob = f"{pack.label} {pack.description}".lower()
        for word in banned:
            assert word not in blob, f"{pack.name} user copy still says {word!r}"


def test_sale_catalog_excludes_retired_packs() -> None:
    assert {pack.name for pack in CREDIT_PACK_CATALOG} == {
        "video_10",
        "video_25",
        "image_50",
        "voice_30m",
    }
    retired = {pack.name for pack in RETIRED_CREDIT_PACKS}
    assert retired == {"lipsync_10", "scripts_25", "creator_burst"}
    for name in retired:
        assert sale_credit_pack_for(name) is None
        assert credit_pack_for(name) is not None


def test_iap_sale_catalog_omits_retired_apple_ids() -> None:
    from app.iap_catalog import default_iap_catalog, product_by_apple_id

    pack_skus = {p.sku for p in default_iap_catalog() if p.kind == "pack"}
    assert pack_skus == {"video_10", "video_25", "image_50", "voice_30m"}
    retired = product_by_apple_id("com.example.studio.credit.lipsync_10")
    assert retired is not None
    assert retired.sku == "lipsync_10"
    assert product_by_apple_id("com.example.studio.credit.scripts_25") is not None
    assert product_by_apple_id("com.example.studio.credit.creator_burst") is not None
