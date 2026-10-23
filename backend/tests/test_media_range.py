"""HTTP Range parsing + client playable clip URLs for progressive streaming."""

from types import SimpleNamespace
from unittest.mock import patch

from app.media_signing import client_playable_media_url, sign_media_url
from app.routers.media import _parse_bytes_range


def test_parse_open_ended_range():
    assert _parse_bytes_range("bytes=0-", 1000) == (0, 999)


def test_parse_closed_range():
    assert _parse_bytes_range("bytes=0-1023", 5000) == (0, 1023)


def test_parse_suffix():
    assert _parse_bytes_range("bytes=-100", 500) == (400, 499)


def test_parse_clamps_end():
    assert _parse_bytes_range("bytes=100-9999", 500) == (100, 499)


def test_parse_invalid():
    assert _parse_bytes_range(None, 100) is None
    assert _parse_bytes_range("bytes=abc-def", 100) is None
    assert _parse_bytes_range("bytes=200-100", 100) is None


def _settings(**overrides):
    base = {
        "jwt_signing_key": "test-jwt-secret-key-for-unit-tests-32b",
        "media_signing_key": "test-media-signing-key-32bytes!!",
        "public_api_base_url": "https://api.example.com",
        "r2_enabled": False,
        "r2_public_base_url": "",
        "r2_bucket_name": "test",
        "r2_endpoint_url": "",
        "r2_access_key_id": "",
        "r2_secret_access_key": "",
        "r2_region": "auto",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_client_playable_uses_signed_api_media_not_r2():
    """Default must be /api/media (HEAD+Range), not R2 presign (HEAD 403)."""
    settings = _settings(r2_enabled=True)
    out = client_playable_media_url("/api/media/play/clip.mp4", settings)
    assert out is not None
    assert out.startswith("https://api.example.com/api/media/play/clip.mp4?")
    assert "sig=" in out and "exp=" in out
    assert "r2.cloudflarestorage.com" not in out


def test_client_playable_never_emits_localhost_absolute():
    """Phones cannot load http://localhost media URLs from PUBLIC_API_BASE_URL."""
    settings = _settings(public_api_base_url="http://localhost:3002", r2_enabled=False)
    out = client_playable_media_url("/api/media/play/clip.mp4", settings)
    assert out is not None
    assert out.startswith("/api/media/play/clip.mp4?")
    assert "localhost" not in out
    assert "sig=" in out


def test_client_playable_r2_presign_only_when_opt_in():
    settings = _settings(r2_enabled=True)

    def fake_presign(key, _settings, *, ttl_seconds=0):
        assert key == "play/clip.mp4"
        return f"https://r2.example/play/clip.mp4?X-Amz-Expires={ttl_seconds}"

    with (
        patch("app.media_store.r2_enabled", return_value=True),
        patch("app.media_store.presign_r2_get", side_effect=fake_presign),
        patch("app.media_store.is_public_marketing_key", return_value=False),
    ):
        out = client_playable_media_url("/api/media/play/clip.mp4", settings, prefer_r2_presign=True)
    assert out == "https://r2.example/play/clip.mp4?X-Amz-Expires=7200"


def test_client_playable_leaves_external_cdn():
    settings = _settings()
    external = "https://cdn.provider.example/tmp/out.mp4?token=1"
    assert client_playable_media_url(external, settings) == external


def test_sign_media_absolute_for_images():
    settings = _settings()
    signed = sign_media_url("/api/media/play/still.jpg", settings, absolute=True)
    assert signed is not None
    assert signed.startswith("https://api.example.com/api/media/play/still.jpg?")


def test_sign_media_absolute_falls_back_relative_on_loopback():
    settings = _settings(public_api_base_url="http://127.0.0.1:3002")
    signed = sign_media_url("/api/media/play/still.jpg", settings, absolute=True)
    assert signed is not None
    assert signed.startswith("/api/media/play/still.jpg?")
    assert "127.0.0.1" not in signed


def test_map_generation_clip_url_is_relative_when_public_api_is_tailscale():
    """SPA on https cannot load http://*.ts.net media (mixed content). Keep DTO relative."""
    from datetime import datetime, timezone
    from uuid import uuid4

    from app.routers.play_helpers import map_generation

    settings = _settings(public_api_base_url="http://devbox.example.ts.net:3001")
    asset = SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        asset_metadata={"play_mode": "avatar", "play_platform": "tiktok"},
        storage_url="/api/media/play/clip.mp4",
        provider_url=None,
        asset_type="video",
        status="ready",
        prompt="hi",
        provider="xai",
        source="xai",
        provider_model="grok",
        error_message=None,
        video_project_id=None,
        created_at=datetime.now(timezone.utc),
    )
    dto = map_generation(asset, settings)
    assert dto.url is not None
    assert dto.url.startswith("/api/media/play/clip.mp4?")
    assert "devbox" not in dto.url
    assert dto.url.startswith("http") is False
