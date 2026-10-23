"""Path-scoped signed URLs for local /api/media assets.

Stored URLs remain unsigned (`/api/media/...`). Sign only when exposing to clients
or external providers that cannot send Authorization headers.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.config import Settings
from app.media_store import key_from_storage_url

DEFAULT_MEDIA_TTL_SECONDS = 2 * 60 * 60  # 2 hours for SPA playback
SHARE_MEDIA_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days for share snapshots
PROVIDER_MEDIA_TTL_SECONDS = 6 * 60 * 60  # 6 hours for provider fetch


def _signing_secret(settings: Settings) -> bytes:
    # Prefer dedicated media key so JWT rotation does not invalidate every signed URL.
    secret = (settings.media_signing_key or settings.jwt_signing_key or "").strip()
    return secret.encode("utf-8")


def _normalize_key(key: str) -> str:
    return "/".join(part for part in key.split("/") if part and part not in {".", ".."})


def media_signature(key: str, exp: int, settings: Settings) -> str:
    key = _normalize_key(key)
    message = f"{key}:{exp}".encode("utf-8")
    return hmac.new(_signing_secret(settings), message, hashlib.sha256).hexdigest()


def verify_media_signature(key: str, exp: int | str | None, sig: str | None, settings: Settings) -> bool:
    if not sig or exp is None:
        return False
    try:
        exp_int = int(exp)
    except (TypeError, ValueError):
        return False
    if exp_int < int(time.time()):
        return False
    expected = media_signature(key, exp_int, settings)
    return hmac.compare_digest(expected, sig)


def strip_media_query(url: str) -> str:
    """Remove exp/sig (and legacy access_token) from a media URL for storage comparison."""
    if not url or not url.startswith("/api/media/"):
        parsed = urlsplit(url)
        if not parsed.path.startswith("/api/media/"):
            return url
        query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in {"exp", "sig", "access_token", "token"}]
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), parsed.fragment))
    parsed = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in {"exp", "sig", "access_token", "token"}]
    return urlunsplit(("", "", parsed.path, urlencode(query), parsed.fragment))


def _public_api_base_is_device_reachable(settings: Settings) -> bool:
    """False for localhost/loopback — phones cannot load those media URLs."""
    base = (settings.public_api_base_url or "").strip()
    if not base:
        return False
    host = (urlsplit(base).hostname or "").lower()
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        return False
    if host.endswith(".local"):
        return False
    return True


def sign_media_url(
    url: str | None,
    settings: Settings,
    *,
    ttl_seconds: int = DEFAULT_MEDIA_TTL_SECONDS,
    absolute: bool = False,
) -> str | None:
    """Return a signed media URL when the target is local /api/media storage.

    Prefer **relative** ``/api/media/...?exp=&sig=`` so mobile/web join their own
    API origin. Absolute only when PUBLIC_API_BASE_URL is not loopback (never
    emit http://localhost — Expo Go on a phone cannot reach it).
    """
    if not url:
        return url
    # Already signed with query params — re-sign from clean key
    clean = strip_media_query(url)
    key = key_from_storage_url(clean, settings)
    if key is None:
        return url

    # Already an absolute https URL that is not our /api/media path (e.g. provider CDN).
    if (clean.startswith("http://") or clean.startswith("https://")) and "/api/media/" not in urlsplit(clean).path:
        # Optional public marketing CDN (examples/) — leave as-is.
        public_base = (settings.r2_public_base_url or "").rstrip("/")
        if public_base and clean.startswith(f"{public_base}/"):
            return url
        return url

    # Only sign local /api/media paths (canonical private storage reference).
    if not clean.startswith("/api/media/") and "/api/media/" not in urlsplit(clean).path:
        return url

    key = _normalize_key(key)
    exp = int(time.time()) + max(60, int(ttl_seconds))
    sig = media_signature(key, exp, settings)
    path = f"/api/media/{key}"
    query = urlencode({"exp": str(exp), "sig": sig})
    signed = f"{path}?{query}"
    # Never bake localhost into client-facing absolute URLs.
    if absolute and _public_api_base_is_device_reachable(settings):
        return f"{settings.public_api_base_url.rstrip('/')}{signed}"
    return signed


def client_playable_media_url(
    url: str | None,
    settings: Settings,
    *,
    ttl_seconds: int = DEFAULT_MEDIA_TTL_SECONDS,
    prefer_r2_presign: bool = False,
) -> str | None:
    """URL safe for native video players (iOS AVPlayer / Expo Video).

    Returns path-signed ``/api/media`` (relative unless PUBLIC_API_BASE_URL is a
    real host the phone can reach). Mobile joins with its API_BASE_URL
    (Tailscale / LAN / production). Never return R2 presign for app play
    (GET-only sig → HEAD 403 on AVPlayer).
    """
    if not url:
        return url

    clean = strip_media_query(url)
    key = key_from_storage_url(clean, settings)

    # External https (provider CDN, marketing) — leave alone.
    if (clean.startswith("http://") or clean.startswith("https://")) and (
        key is None or "/api/media/" not in urlsplit(clean).path
    ):
        public_base = (settings.r2_public_base_url or "").rstrip("/")
        if public_base and clean.startswith(f"{public_base}/"):
            return clean
        if key is None:
            return clean

    # Optional R2 presign is opt-in for non-player use cases only.
    if prefer_r2_presign and key:
        from app.media_store import MediaStoreError, is_public_marketing_key, presign_r2_get, r2_enabled

        if r2_enabled(settings) and not is_public_marketing_key(key):
            try:
                return presign_r2_get(key, settings, ttl_seconds=ttl_seconds)
            except MediaStoreError:
                pass

    path = clean if clean.startswith("/api/media/") else (f"/api/media/{key}" if key else clean)
    # Relative when local; absolute only for real public hosts (prod).
    return sign_media_url(path, settings, ttl_seconds=ttl_seconds, absolute=True) or path


# Media URL fields commonly stored in asset/play metadata (unsigned on disk).
ASSET_METADATA_MEDIA_KEYS: tuple[str, ...] = (
    "poster_url",
    "clip_poster_url",
    "face_image_url",
    "last_frame_url",
    "image_url",
    "thumb_url",
    "thumbnail_url",
    "download_url",
    "media_url",
)


def sign_media_fields(payload: dict, settings: Settings, *, keys: tuple[str, ...] = (), ttl_seconds: int = DEFAULT_MEDIA_TTL_SECONDS) -> dict:
    """Sign known media URL fields in a shallow dict (e.g. share snapshots)."""
    if not keys:
        keys = (
            "download_url",
            "output_url",
            "storage_url",
            "url",
            "pdf_url",
            "logo_url",
            "media_url",
            "provider_url",
            *ASSET_METADATA_MEDIA_KEYS,
        )
    out = dict(payload)
    for key in keys:
        if key in out and isinstance(out[key], str):
            out[key] = sign_media_url(out[key], settings, ttl_seconds=ttl_seconds) or out[key]
    return out
