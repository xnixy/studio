"""Talking + clone chain: spoken line required, Grok never gets a clone id."""
from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.routers.play_talking_clone import generate_talking_clone
from app.routers.play_video_helpers import split_avatar_user_prompt
from app.routers.play_voices import ResolvedTtsVoice, standin_voice_id
from app.xai_media import build_xai_video_payload


def test_spoken_line_required_for_clone_talking() -> None:
    spoken, scene = split_avatar_user_prompt("Kitchen island, soft light, black tee.")
    assert spoken == ""
    assert "Kitchen" in scene


def test_spoken_line_splits_when_present() -> None:
    spoken, scene = split_avatar_user_prompt(
        "Kitchen island, soft light. She says: free shipping this week."
    )
    assert "free shipping" in spoken
    assert "Kitchen" in scene


def test_standin_never_equals_elevenlabs_id() -> None:
    settings = Settings()
    clone_id = "21m00Tcm4TlvDq8ikWAM"
    assert standin_voice_id("female", settings) != clone_id
    payload = build_xai_video_payload(
        model="grok-imagine-video-1.5",
        prompt="talk",
        duration=6,
        aspect_ratio="9:16",
        resolution="720p",
        reference_audio_voice_ids=[standin_voice_id("male", settings)],
    )
    assert payload["reference_audios"] == [{"voice_id": "rex"}]


@pytest.mark.asyncio
async def test_talking_clone_rejects_empty_line() -> None:
    resolved = ResolvedTtsVoice(
        provider_voice_id="el-voice",
        workspace_voice_id=uuid4(),
        provider="elevenlabs",
        gender="female",
        language="en",
        is_clone=True,
    )
    with pytest.raises(HTTPException) as exc:
        await generate_talking_clone(
            session=SimpleNamespace(),  # type: ignore[arg-type]
            settings=Settings(),
            user=SimpleNamespace(id=uuid4()),  # type: ignore[arg-type]
            body=SimpleNamespace(
                face_asset_id=uuid4(),
                workspace_id=uuid4(),
                voice=str(uuid4()),
            ),  # type: ignore[arg-type]
            project=SimpleNamespace(),  # type: ignore[arg-type]
            play_model=SimpleNamespace(provider_model="seedance-2-0-fast", id="seedance-avatar-fast", max_duration_seconds=15),
            prompt="A sunny kitchen, no spoken line.",
            aspect_ratio="9:16",
            resolved=resolved,
        )
    assert exc.value.status_code == 422
    assert "spoken line" in str(exc.value.detail).lower()


@pytest.mark.asyncio
async def test_scene_voice_rejects_unquoted_prompt() -> None:
    from app.routers.play_scene_voice import generate_scene_voice

    resolved = ResolvedTtsVoice(
        provider_voice_id="el-voice",
        workspace_voice_id=None,
        provider="elevenlabs",
        gender="female",
        language="en",
        is_clone=False,
    )
    with pytest.raises(HTTPException) as exc:
        await generate_scene_voice(
            session=SimpleNamespace(),  # type: ignore[arg-type]
            settings=Settings(),
            user=SimpleNamespace(id=uuid4()),  # type: ignore[arg-type]
            body=SimpleNamespace(
                face_asset_id=uuid4(),
                workspace_id=uuid4(),
                voice="jessica",
            ),  # type: ignore[arg-type]
            project=SimpleNamespace(),  # type: ignore[arg-type]
            play_model=SimpleNamespace(id="seedance-2-0-fast", provider_model="seedance-2-0-fast", max_duration_seconds=15),
            prompt="Two friends talk about the new drop.",
            aspect_ratio="9:16",
            resolved=resolved,
        )
    assert exc.value.status_code == 422
