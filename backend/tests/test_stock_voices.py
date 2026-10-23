"""Stock ElevenLabs catalog, fallback from retired xAI ids, clip purge rules."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.config import Settings
from app.routers.play_voices import (
    ResolvedTtsVoice,
    _builtin_voices,
    grok_safe_voice_id,
    resolve_tts_voice,
    standin_voice_id,
)
from app.stock_voices import (
    DEFAULT_STOCK_VOICE_ID,
    DEFAULT_STOCK_VOICE_IDS,
    FEATURED_VOICE_IDS,
    LEGACY_XAI_VOICE_IDS,
    LIBRARY_VOICES,
    STOCK_VOICES,
    elevenlabs_voice_id_for,
    should_purge_legacy_stock_clip,
    stock_voice_id_for,
)
from app.xai_media import build_xai_video_payload


def test_stock_catalog_uses_human_names_not_xai() -> None:
    voices = _builtin_voices()
    ids = {v.id for v in voices}
    assert DEFAULT_STOCK_VOICE_ID in ids
    assert set(FEATURED_VOICE_IDS).issubset(ids)
    assert "charlie" in ids and "aria" in ids and "river" in ids
    assert "ara" not in ids
    assert "rex" not in ids
    assert all(v.source == "builtin" and v.provider == "elevenlabs" for v in voices)
    assert all(v.provider_voice_id and v.provider_voice_id != v.id for v in voices)


def test_old_xai_ids_fall_back_to_default() -> None:
    assert stock_voice_id_for("ara") == DEFAULT_STOCK_VOICE_ID
    assert stock_voice_id_for("rex") == DEFAULT_STOCK_VOICE_ID
    assert stock_voice_id_for("jessica") == "jessica"
    assert stock_voice_id_for("male") == "brian"
    assert stock_voice_id_for("") == DEFAULT_STOCK_VOICE_ID
    el = elevenlabs_voice_id_for("jessica")
    assert el == STOCK_VOICES["jessica"]["elevenlabs_voice_id"]
    assert el != "jessica"


def test_purge_legacy_stock_clips_keeps_clones_and_video() -> None:
    clone_id = str(uuid4())
    assert should_purge_legacy_stock_clip(play_mode="avatar", voice="ara") is True
    assert should_purge_legacy_stock_clip(play_mode="lipsync", voice="rex") is True
    assert should_purge_legacy_stock_clip(play_mode="avatar", voice="") is True
    assert should_purge_legacy_stock_clip(play_mode="avatar", voice=clone_id) is False
    assert should_purge_legacy_stock_clip(play_mode="video", voice="ara") is False
    assert should_purge_legacy_stock_clip(play_mode="lipsync", voice=clone_id) is False
    assert should_purge_legacy_stock_clip(play_mode="avatar", voice="jessica") is False
    assert "ara" in LEGACY_XAI_VOICE_IDS
    face_meta = {"play_mode": "avatar", "mode": "avatar_source_image", "face_library": True}
    assert should_purge_legacy_stock_clip(
        play_mode="avatar", voice="", asset_type="image", metadata=face_meta
    ) is False
    assert should_purge_legacy_stock_clip(
        play_mode="avatar", voice="", asset_type="image"
    ) is False


def test_purge_legacy_ids_match_migration() -> None:
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "alembic/versions/0043_purge_xai_stock_clips.py"
    spec = importlib.util.spec_from_file_location("purge_xai_stock_clips", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert set(mod._LEGACY) == set(LEGACY_XAI_VOICE_IDS)


def test_grok_safe_voice_never_uses_elevenlabs_id() -> None:
    settings = Settings()
    stock = ResolvedTtsVoice(
        provider_voice_id=elevenlabs_voice_id_for("jessica"),
        workspace_voice_id=None,
        provider="elevenlabs",
        gender="female",
        language="en",
        is_clone=False,
    )
    clone = ResolvedTtsVoice(
        provider_voice_id="21m00Tcm4TlvDq8ikWAM",
        workspace_voice_id=uuid4(),
        provider="elevenlabs",
        gender="male",
        language="en",
        is_clone=True,
    )
    assert grok_safe_voice_id(stock, settings) == "ara"
    assert grok_safe_voice_id(clone, settings) == "rex"
    payload = build_xai_video_payload(
        model="grok-imagine-video-1.5",
        prompt="talk",
        duration=8,
        aspect_ratio="9:16",
        resolution="720p",
        reference_audio_voice_ids=[grok_safe_voice_id(stock, settings)],
    )
    assert payload["reference_audios"] == [{"voice_id": "ara"}]
    assert standin_voice_id("female", settings) == "ara"


@pytest.mark.asyncio
async def test_stock_resolve_uses_elevenlabs_not_xai() -> None:
    settings = Settings()
    resolved = await resolve_tts_voice(
        session=SimpleNamespace(),  # type: ignore[arg-type]
        workspace_id=uuid4(),
        voice="jessica",
        settings=settings,
    )
    assert resolved.is_clone is False
    assert resolved.provider == "elevenlabs"
    assert resolved.provider_voice_id == elevenlabs_voice_id_for("jessica")
    leftover = await resolve_tts_voice(
        session=SimpleNamespace(),  # type: ignore[arg-type]
        workspace_id=uuid4(),
        voice="ara",
        settings=settings,
    )
    assert leftover.provider == "elevenlabs"
    assert leftover.provider_voice_id == elevenlabs_voice_id_for(DEFAULT_STOCK_VOICE_ID)


def test_library_voices_extend_hosted_catalog() -> None:
    assert len(LIBRARY_VOICES) >= 60
    assert len(STOCK_VOICES) == len(DEFAULT_STOCK_VOICE_IDS) + len(LIBRARY_VOICES)
    assert DEFAULT_STOCK_VOICE_IDS.isdisjoint(LIBRARY_VOICES)
    assert "hope" in LIBRARY_VOICES
    assert stock_voice_id_for("hope") == "hope"
    assert elevenlabs_voice_id_for("hope") == LIBRARY_VOICES["hope"]["elevenlabs_voice_id"]
    assert elevenlabs_voice_id_for("hope") != "hope"
    voices = _builtin_voices()
    accents = {v.accent for v in voices if v.accent}
    assert "american" in accents and "british" in accents and "indian" in accents
    assert all(v.id not in LEGACY_XAI_VOICE_IDS for v in voices)
    assert all((v.provider_voice_id or "") != v.id for v in voices)
