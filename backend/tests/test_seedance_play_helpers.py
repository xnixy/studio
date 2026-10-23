"""Unit tests for Seedance play material limits and request shape."""
from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.routers.play_video_helpers import (
    MAX_REF_AUDIOS,
    MAX_REF_IMAGES,
    MAX_REF_TOTAL,
    MAX_REF_VIDEOS,
    normalize_play_resolution,
)
from app.schemas.play import PlayGenerateRequest, PlayGenerateResponse, PlayGenerationDto
from datetime import datetime, timezone


def test_normalize_seedance_resolution() -> None:
    assert normalize_play_resolution("4K", provider="seedance") == "4k"
    assert normalize_play_resolution("1080", provider="seedance") == "1080p"
    assert normalize_play_resolution(None, provider="xai") == "720p"
    assert (
        normalize_play_resolution("1080p", provider="seedance", model_id="seedance-2-5") == "720p"
    )
    assert (
        normalize_play_resolution("4k", provider="seedance", model_id="seedance-avatar") == "720p"
    )


def test_seedance_25_duration_and_seed_rules() -> None:
    from app.seedance_media import clamp_seedance_duration, is_seedance_25

    assert is_seedance_25("seedance-2-5")
    assert is_seedance_25("seedance-avatar")
    assert is_seedance_25("seedance-photo")
    assert not is_seedance_25("seedance-2-0")
    assert not is_seedance_25("seedance-avatar-fast")
    assert not is_seedance_25("seedance-photo-fast")
    assert clamp_seedance_duration(30, model="seedance-2-5") == 30
    assert clamp_seedance_duration(30, model="seedance-2-0") == 15


def test_play_generate_request_batch_and_refs() -> None:
    body = PlayGenerateRequest(
        workspace_id=uuid4(),
        prompt="a product spin",
        count=3,
        return_last_frame=True,
        reference_asset_ids=[uuid4(), uuid4()],
        continue_from_asset_id=uuid4(),
    )
    assert body.count == 3
    assert body.return_last_frame is True
    assert len(body.reference_asset_ids) == 2
    assert body.continue_from_asset_id is not None


def test_play_generate_request_rejects_too_many_refs() -> None:
    with pytest.raises(ValidationError):
        PlayGenerateRequest(
            workspace_id=uuid4(),
            prompt="x",
            reference_asset_ids=[uuid4() for _ in range(13)],
        )


def test_play_generate_response_generations_compat() -> None:
    now = datetime.now(timezone.utc)
    dto = PlayGenerationDto(
        id=uuid4(),
        workspace_id=uuid4(),
        mode="video",
        platform="tiktok",
        prompt="hi",
        status="processing",
        asset_type="video",
        created_at=now,
    )
    res = PlayGenerateResponse(generation=dto, generations=[dto, dto], message="Started 2 variants.")
    assert res.generation.id == res.generations[0].id
    assert len(res.generations) == 2


def test_material_cap_constants_match_docs() -> None:
    assert MAX_REF_IMAGES == 9
    assert MAX_REF_VIDEOS == 3
    assert MAX_REF_AUDIOS == 3
    assert MAX_REF_TOTAL == 12
