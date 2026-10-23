"""Custom voices: clone cap, stand-in ids, quotes, edit guards, OpenAPI."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI

from app.config import Settings
from app.play_pricing import compute_play_quote
from app.routers.play import router as play_router
from app.routers.play_face_edit import _reject_edit_instruction, face_edit_prompt
from app.routers.play_voices import (
    _builtin_voices,
    classify_face_bind_voice_id,
    clone_cap_for_workspace,
    custom_voices_access,
    standin_voice_id,
)
from app.sync_labs import create_sync_labs_video_dub, sync_opens_silent_lips
from app.xai_media import build_xai_video_payload


def test_builtin_voices_include_flagship_set() -> None:
    voices = _builtin_voices()
    ids = {v.id for v in voices}
    assert {"jessica", "lily", "brian", "daniel", "liam"}.issubset(ids)
    assert {"aria", "charlotte", "charlie", "callum", "river"}.issubset(ids)
    assert len(ids) >= 19
    assert all(v.source == "builtin" and v.provider == "elevenlabs" for v in voices)


def test_play_face_bind_request_accepts_stock_name() -> None:
    from datetime import UTC, datetime

    from app.schemas.play import PlayFaceBindVoiceRequest, PlayFaceDto

    body = PlayFaceBindVoiceRequest(workspace_id=uuid4(), bound_voice_id="jessica")
    assert body.bound_voice_id == "jessica"
    dto = PlayFaceDto(
        id=uuid4(),
        workspace_id=uuid4(),
        created_at=datetime.now(UTC),
        bound_voice_id="jessica",
    )
    assert dto.bound_voice_id == "jessica"


def test_classify_face_bind_accepts_stock_and_clone_ids() -> None:
    assert classify_face_bind_voice_id(None) == ("none", None)
    assert classify_face_bind_voice_id("  ") == ("none", None)
    assert classify_face_bind_voice_id("jessica") == ("stock", "jessica")
    assert classify_face_bind_voice_id("Brian") == ("stock", "brian")
    uid = str(uuid4())
    assert classify_face_bind_voice_id(uid) == ("clone", uid)
    with pytest.raises(ValueError):
        classify_face_bind_voice_id("not-a-voice")


def test_clone_cap_defaults_to_one() -> None:
    assert clone_cap_for_workspace(SimpleNamespace(limit_overrides=None)) == 1
    assert clone_cap_for_workspace(SimpleNamespace(limit_overrides={})) == 1
    assert clone_cap_for_workspace(SimpleNamespace(limit_overrides={"clone_slot_limit": 3})) == 3
    assert clone_cap_for_workspace(SimpleNamespace(limit_overrides={"clone_slot_limit": 0})) == 0


def test_custom_voices_access_self_serve() -> None:
    open_slot = custom_voices_access(clone_cap=1, clone_count=0)
    assert open_slot.can_clone is True
    assert open_slot.clone_cap == 1
    at_cap = custom_voices_access(clone_cap=1, clone_count=1)
    assert at_cap.can_clone is False
    raised = custom_voices_access(clone_cap=2, clone_count=1)
    assert raised.can_clone is True


def test_standin_voice_is_ara_or_rex() -> None:
    settings = Settings()
    assert standin_voice_id("female", settings) == "ara"
    assert standin_voice_id("male", settings) == "rex"
    assert standin_voice_id("neutral", settings) == "ara"
    assert standin_voice_id(None, settings) == "ara"


def test_talking_clone_quote_does_not_add_lipsync() -> None:
    plain = compute_play_quote(mode="avatar", model_id="seedance-avatar-fast", duration_seconds=8)
    cloned = compute_play_quote(
        mode="avatar",
        model_id="seedance-avatar-fast",
        duration_seconds=8,
        cloned_voice=True,
    )
    assert cloned.total == plain.total
    assert cloned.breakdown["cloned_voice"] is True
    assert "lipsync_tokens" not in cloned.breakdown
    assert cloned.breakdown["voiceover_seconds"] >= 5
    chris = compute_play_quote(mode="avatar", model_id="seedance-avatar-fast", duration_seconds=8)
    assert "cloned_voice" not in chris.breakdown


def test_scene_clone_quote_does_not_add_lipsync() -> None:
    plain = compute_play_quote(mode="video", model_id="seedance-2-0-fast", duration_seconds=8)
    cloned = compute_play_quote(
        mode="video",
        model_id="seedance-2-0-fast",
        duration_seconds=8,
        cloned_voice=True,
    )
    assert cloned.total == plain.total
    assert cloned.breakdown["cloned_voice"] is True
    assert "lipsync_tokens" not in cloned.breakdown


def test_face_edit_rejects_scene_and_identity() -> None:
    assert _reject_edit_instruction("", kind="touchup")
    assert _reject_edit_instruction("different person smiling", kind="touchup")
    assert _reject_edit_instruction("in Tokyo at night", kind="look")
    assert _reject_edit_instruction("Polish the skin", kind="touchup") is None


def test_face_edit_prompt_keeps_identity() -> None:
    touch = face_edit_prompt(instruction="softer skin", kind="touchup")
    look = face_edit_prompt(instruction="black blazer", kind="look")
    assert "Same clothes" in touch
    assert "black blazer" in look
    assert "Same person" in look or "keep identity" in look.lower()


def test_grok_payload_never_uses_elevenlabs_shaped_ids() -> None:
    payload = build_xai_video_payload(
        model="grok-imagine-video-1.5",
        prompt="talk",
        duration=8,
        aspect_ratio="9:16",
        resolution="720p",
        reference_audio_voice_ids=["ara"],
    )
    assert payload["reference_audios"] == [{"voice_id": "ara"}]


def test_openapi_drops_waitlist_and_starters_and_adds_edit() -> None:
    app = FastAPI()
    app.include_router(play_router)
    paths = set(app.openapi()["paths"])
    assert "/play/faces/starters" not in paths
    assert "/play/faces/from-starter" not in paths
    assert "/play/voices/waitlist" not in paths
    assert "/play/voices/waitlist/me" not in paths
    assert "/play/faces/{face_id}/edit" in paths
    assert "/play/voices/clone" in paths
    assert "/play/faces/{face_id}/voice" in paths
    bind_schema = app.openapi()["components"]["schemas"]["PlayFaceBindVoiceRequest"]["properties"][
        "bound_voice_id"
    ]
    dumped = str(bind_schema).lower()
    assert "uuid" not in dumped
    assert "string" in dumped


@pytest.mark.asyncio
async def test_sync_video_dub_payload_uses_video_type(monkeypatch) -> None:
    captured: dict = {}

    async def fake_json(method, url, settings, *, timeout, json=None):
        captured["payload"] = json
        return {"id": "sync-1", "status": "PENDING"}

    monkeypatch.setattr("app.sync_labs.sync_labs_json", fake_json)
    settings = SimpleNamespace(
        sync_labs_api_key="k", sync_labs_model="sync-3", sync_labs_base_url="https://api.sync.so"
    )
    result = await create_sync_labs_video_dub(
        video_url="https://example.com/v.mp4",
        audio_url="https://example.com/a.mp3",
        settings=settings,  # type: ignore[arg-type]
        output_name="talk",
    )
    assert result.request_id == "sync-1"
    kinds = [row["type"] for row in captured["payload"]["input"]]
    assert kinds == ["video", "audio"]
    opts = captured["payload"]["options"]
    assert opts["sync_mode"] == "cut_off"
    assert opts["active_speaker_detection"]["auto_detect"] is True


def test_sync_3_can_open_still_mouths() -> None:
    assert sync_opens_silent_lips(SimpleNamespace(sync_labs_model="sync-3")) is True
    assert sync_opens_silent_lips(SimpleNamespace(sync_labs_model="sync-3.0")) is True
    assert sync_opens_silent_lips(SimpleNamespace(sync_labs_model="lipsync-2")) is False
    assert sync_opens_silent_lips(SimpleNamespace(sync_labs_model="")) is True


def test_mute_quote_is_only_for_user_requested_silence() -> None:
    voiced = compute_play_quote(mode="avatar", model_id="seedance-avatar-fast", duration_seconds=8)
    mute = compute_play_quote(
        mode="avatar",
        model_id="seedance-avatar-fast",
        duration_seconds=8,
        generate_audio=False,
    )
    assert voiced.breakdown["audio_factor"] == 1.0
    assert mute.breakdown["audio_factor"] == 0.9
