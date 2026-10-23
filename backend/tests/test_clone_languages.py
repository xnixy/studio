"""Clone language allowlist and ElevenLabs audio error mapping."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.clone_languages import (
    ALLOWED_CLONE_LANGUAGES,
    normalize_clone_language,
    preview_script_for,
)
from app.elevenlabs_voices import _friendly_error


ROOT = Path(__file__).resolve().parents[2]


def test_normalize_clone_language_strips_region() -> None:
    assert normalize_clone_language("en-US") == "en"
    assert normalize_clone_language("pt_BR") == "pt"
    assert normalize_clone_language("ZH") == "zh"
    assert normalize_clone_language("tl") == "fil"
    assert normalize_clone_language("nb") == "no"


def test_elevenlabs_tts_uses_v3() -> None:
    from app.elevenlabs_voices import ELEVENLABS_TTS_MODEL

    assert ELEVENLABS_TTS_MODEL == "eleven_v3"


def test_normalize_clone_language_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="supported language"):
        normalize_clone_language("xx")


def test_preview_script_matches_language() -> None:
    assert "preview" in preview_script_for("en").lower()
    assert preview_script_for("es") != preview_script_for("en")
    assert preview_script_for("ja") != preview_script_for("en")


def test_client_clone_language_lists_match_backend() -> None:
    web = ROOT / "frontend/src/features/play/cloneVoice.ts"
    mobile = ROOT / "mobile/src/lib/cloneVoice.ts"
    if not web.is_file() or not mobile.is_file():
        pytest.skip("client trees are not present")
    web_codes = set(re.findall(r'code: "([a-z]{2,3})"', web.read_text(encoding="utf-8")))
    mobile_codes = set(re.findall(r'code: "([a-z]{2,3})"', mobile.read_text(encoding="utf-8")))
    assert web_codes == ALLOWED_CLONE_LANGUAGES
    assert mobile_codes == ALLOWED_CLONE_LANGUAGES


def test_elevenlabs_corrupted_audio_is_friendly() -> None:
    err = _friendly_error(
        400,
        '{"detail":{"status":"invalid_audio_file","message":"The audio file is corrupted. Please ensure it is playable audio."}}',
    )
    assert err.status_code == 400
    assert "HTTP 400" not in str(err)
    assert "recording" in str(err).lower()
