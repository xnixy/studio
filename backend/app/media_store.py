from __future__ import annotations

import base64
import mimetypes
import re
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

from app.config import Settings


class MediaStoreError(RuntimeError):
    pass


def safe_media_name(value: object) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value)).strip("-").lower()
    return text[:80] or "asset"


def extension_from_url(url: str, fallback: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".m4v", ".mp3", ".wav", ".vtt", ".srt", ".ass"}:
        return suffix
    return fallback if fallback.startswith(".") else f".{fallback}"


def content_type_for_key(key: str) -> str:
    guessed, _ = mimetypes.guess_type(key)
    if guessed:
        return guessed
    lower = key.lower()
    if lower.endswith(".mp3"):
        return "audio/mpeg"
    if lower.endswith(".mp4"):
        return "video/mp4"
    if lower.endswith(".webm"):
        return "video/webm"
    if lower.endswith(".jpg") or lower.endswith(".jpeg"):
        return "image/jpeg"
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".vtt"):
        return "text/vtt"
    if lower.endswith(".srt"):
        return "application/x-subrip"
    return "application/octet-stream"


def media_key(subdir: str, filename: str) -> str:
    clean_subdir = "/".join(part for part in Path(subdir).as_posix().split("/") if part not in {"", ".", ".."})
    clean_name = Path(filename).name
    if not clean_name or clean_name in {".", ".."}:
        raise MediaStoreError("Invalid media filename")
    return f"{clean_subdir}/{clean_name}" if clean_subdir else clean_name


def r2_enabled(settings: Settings) -> bool:
    return settings.r2_enabled


@lru_cache(maxsize=4)
def _r2_client_cached(endpoint: str, access_key_id: str, secret_access_key: str, region: str) -> Any:
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise MediaStoreError("boto3 is required for Cloudflare R2 storage. Install backend requirements.") from exc

    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    )


def r2_client(settings: Settings) -> Any:
    if not settings.r2_enabled:
        raise MediaStoreError("Cloudflare R2 is not configured")
    return _r2_client_cached(
        settings.r2_endpoint,
        settings.r2_access_key_id or "",
        settings.r2_secret_access_key or "",
        settings.r2_region,
    )


def public_url_for_key(key: str, settings: Settings) -> str:
    """Canonical storage URL for user media (always ACL-gated via /api/media).

    Marketing/public objects under examples/ may still use R2_PUBLIC_BASE_URL
    at the call site; store_bytes always returns the private API path.
    """
    _ = settings  # settings kept for call-site stability
    return f"/api/media/{key.lstrip('/')}"


def is_public_marketing_key(key: str) -> bool:
    """Keys under examples/ are intentional public marketing assets."""
    cleaned = key.lstrip("/")
    return cleaned == "examples" or cleaned.startswith("examples/")


def presign_r2_get(key: str, settings: Settings, *, ttl_seconds: int = 6 * 60 * 60) -> str:
    """Time-limited HTTPS GET for private R2 objects (providers that cannot send JWT)."""
    client = r2_client(settings)
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": key.lstrip("/")},
            ExpiresIn=max(60, int(ttl_seconds)),
        )
    except Exception as exc:  # noqa: BLE001
        raise MediaStoreError(f"Failed to presign R2 object: {exc}") from exc


def media_url_for(path: Path, settings: Settings) -> str:
    relative = path.resolve().relative_to(settings.media_path.resolve()).as_posix()
    return public_url_for_key(relative, settings)


def local_path_for_key(key: str, settings: Settings) -> Path:
    parts = [part for part in key.split("/") if part and part not in {".", ".."}]
    if not parts:
        raise MediaStoreError("Invalid media key")
    return settings.media_path.joinpath(*parts)


def key_from_storage_url(url: str, settings: Settings) -> str | None:
    if not url:
        return None
    # Strip query/signature fragments so signed URLs still resolve to a storage key.
    bare = url.split("?", 1)[0].split("#", 1)[0]
    if bare.startswith("/api/media/"):
        return bare[len("/api/media/") :].lstrip("/")
    public_base = (settings.r2_public_base_url or "").rstrip("/")
    if public_base and bare.startswith(f"{public_base}/"):
        return bare[len(public_base) + 1 :].lstrip("/")
    parsed = urlparse(bare)
    if parsed.path.startswith("/api/media/"):
        return parsed.path[len("/api/media/") :].lstrip("/")
    return None


def local_path_from_media_url(url: str, settings: Settings) -> Path | None:
    key = key_from_storage_url(url, settings)
    if key is None:
        return None
    return local_path_for_key(key, settings)


def public_media_url(url: str, settings: Settings) -> str:
    """Absolute URL for external providers.

    Private user media: R2 presigned GET when R2 is enabled, otherwise path-signed
    /api/media URL. Never emit permanent public R2 object URLs for user content.
    """
    from app.media_signing import PROVIDER_MEDIA_TTL_SECONDS, sign_media_url, strip_media_query

    if not url:
        return url
    clean = strip_media_query(url)
    parsed = urlparse(clean)
    is_local_media = clean.startswith("/api/media/") or parsed.path.startswith("/api/media/")
    if (clean.startswith("http://") or clean.startswith("https://")) and not is_local_media:
        return clean
    if is_local_media:
        key = key_from_storage_url(clean, settings)
        if key and settings.r2_enabled:
            if is_public_marketing_key(key) and settings.r2_public_base_url:
                return f"{settings.r2_public_base_url.rstrip('/')}/{key.lstrip('/')}"
            return presign_r2_get(key, settings, ttl_seconds=PROVIDER_MEDIA_TTL_SECONDS)
        signed = sign_media_url(clean, settings, ttl_seconds=PROVIDER_MEDIA_TTL_SECONDS, absolute=True)
        return signed or clean
    if clean.startswith("/"):
        return f"{settings.public_api_base_url.rstrip('/')}{clean}"
    return clean


def _host_is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local")


def _is_ephemeral_provider_cdn(url: str) -> bool:
    """Temporary vendor CDN URLs (xAI imgen tmp, etc.) expire and must not win over storage_url."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    host = (parsed.hostname or "").lower()
    path = (parsed.path or "").lower()
    if host.endswith("imgen.x.ai") or host.endswith("x.ai") and "imgen" in host:
        return True
    if "xai-tmp" in path or "xai-imgen" in path or "/tmp-" in path:
        return True
    return False


def xai_image_ref(
    *,
    storage_url: str | None,
    provider_url: str | None,
    settings: Settings,
    label: str = "Image",
    prefer_data_url: bool = False,
) -> str:
    """Build an image reference providers accept: public https URL or base64 data URL.

    Prefer durable storage_url over temporary provider CDNs (imgen.x.ai expires → 404).
    Local `/api/media/...` and private R2 are inlined as data:image/...;base64,...

    When ``prefer_data_url`` is True (Talking face plates), always embed bytes so the
    provider never has to fetch R2/presigned URLs. Fetch failures look like
    text-only video and invent a different person.
    """
    # Durable first (our /api/media or R2), then provider CDN as last resort.
    durable = [u.strip() for u in (storage_url,) if u and str(u).strip()]
    ephemeral = [
        u.strip()
        for u in (provider_url,)
        if u and str(u).strip() and _is_ephemeral_provider_cdn(u.strip())
    ]
    other = [
        u.strip()
        for u in (provider_url,)
        if u and str(u).strip() and not _is_ephemeral_provider_cdn(u.strip())
    ]
    candidates = durable + other + ephemeral

    def _usable_https(url: str, *, allow_ephemeral: bool) -> str | None:
        if url.startswith("data:image/"):
            return url
        if not (url.startswith("https://") or url.startswith("http://")):
            return None
        if _host_is_loopback(url):
            return None
        if not url.startswith("https://"):
            return None
        if not allow_ephemeral and _is_ephemeral_provider_cdn(url):
            return None
        return url

    # 1) Durable HTTPS (signed /api/media absolute or R2 presign) — skip when
    #    prefer_data_url (identity must travel in the request body).
    if not prefer_data_url:
        for candidate in durable + other:
            hit = _usable_https(candidate, allow_ephemeral=False)
            if hit:
                return hit
            public = public_media_url(candidate, settings)
            hit = _usable_https(public, allow_ephemeral=False)
            if hit and not _is_ephemeral_provider_cdn(hit):
                # Signed API media URLs work for providers that can fetch with query sig.
                # For Veo we still prefer base64 from storage when private.
                if "/api/media/" in hit and "sig=" in hit:
                    pass  # fall through to inline bytes for reliability
                else:
                    return hit

    # 2) Inline durable bytes (local disk / R2) — required for Veo face plates
    #    and for Grok Talking identity (prefer_data_url).
    path: Path | None = None
    raw: bytes | None = None
    mime = "image/jpeg"
    for candidate in durable + other:
        try:
            key = key_from_storage_url(candidate, settings)
            if key:
                local = local_path_for_key(key, settings)
                if local.exists() and local.stat().st_size > 0:
                    path = local
                    raw = local.read_bytes()
                    mime = content_type_for_key(key) or mime
                    break
                if r2_enabled(settings):
                    raw = get_r2_bytes(key, settings)
                    mime = content_type_for_key(key) or mime
                    break
        except Exception:
            continue
        path = local_path_from_media_url(candidate, settings)
        if path is not None and path.exists() and path.stat().st_size > 0:
            raw = path.read_bytes()
            mime = content_type_for_key(path.name) or mime
            break
        path = None

    if raw is None:
        for candidate in durable + other + ephemeral:
            if candidate.startswith("http://") or candidate.startswith("https://"):
                if _is_ephemeral_provider_cdn(candidate):
                    # Skip expired tmp CDNs unless nothing else works (try last).
                    continue
                try:
                    path = ensure_local_media(candidate, settings)
                    if path.exists() and path.stat().st_size > 0:
                        raw = path.read_bytes()
                        mime = content_type_for_key(path.name) or mime
                        break
                except MediaStoreError:
                    continue

    if raw is None:
        # Last resort: ephemeral CDN (often already 404)
        for candidate in ephemeral:
            try:
                path = ensure_local_media(candidate, settings)
                if path.exists() and path.stat().st_size > 0:
                    raw = path.read_bytes()
                    mime = content_type_for_key(path.name) or mime
                    break
            except MediaStoreError:
                continue

    if raw is None or len(raw) == 0:
        raise MediaStoreError(
            f"{label} is not available as a public URL or local file. "
            "Re-upload or regenerate the face (temporary provider links expire)."
        )

    if len(raw) > 12 * 1024 * 1024:
        raise MediaStoreError(f"{label} is too large to send as base64 (max ~12 MB). Use a smaller face image.")
    if not mime.startswith("image/"):
        mime = "image/jpeg"
    encoded = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def write_local_bytes(key: str, content: bytes, settings: Settings) -> Path:
    path = local_path_for_key(key, settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def put_r2_bytes(key: str, content: bytes, settings: Settings, *, content_type: str | None = None) -> None:
    client = r2_client(settings)
    client.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=content,
        ContentType=content_type or content_type_for_key(key),
    )


def put_r2_file(key: str, path: Path, settings: Settings, *, content_type: str | None = None) -> None:
    client = r2_client(settings)
    extra = {"ContentType": content_type or content_type_for_key(key)}
    client.upload_file(str(path), settings.r2_bucket_name, key, ExtraArgs=extra)


def get_r2_bytes(key: str, settings: Settings) -> bytes:
    client = r2_client(settings)
    try:
        response = client.get_object(Bucket=settings.r2_bucket_name, Key=key.lstrip("/"))
    except Exception as exc:  # noqa: BLE001 - surface provider errors cleanly
        raise MediaStoreError(f"Failed to download media from R2: {exc}") from exc
    body = response["Body"].read()
    if not isinstance(body, (bytes, bytearray)):
        raise MediaStoreError("R2 object body was not bytes")
    return bytes(body)


def head_r2_size(key: str, settings: Settings) -> int:
    """Content-Length for an R2 object (bytes)."""
    client = r2_client(settings)
    try:
        response = client.head_object(Bucket=settings.r2_bucket_name, Key=key.lstrip("/"))
    except Exception as exc:  # noqa: BLE001
        raise MediaStoreError(f"Failed to head media from R2: {exc}") from exc
    size = response.get("ContentLength")
    if size is None:
        raise MediaStoreError("R2 head missing ContentLength")
    return int(size)


def get_r2_bytes_range(
    key: str,
    settings: Settings,
    *,
    start: int,
    end: int,
) -> tuple[bytes, int]:
    """Fetch inclusive byte range [start, end] from R2. Returns (chunk, total_size)."""
    if start < 0 or end < start:
        raise MediaStoreError("Invalid byte range")
    client = r2_client(settings)
    try:
        response = client.get_object(
            Bucket=settings.r2_bucket_name,
            Key=key.lstrip("/"),
            Range=f"bytes={start}-{end}",
        )
    except Exception as exc:  # noqa: BLE001
        raise MediaStoreError(f"Failed to range-download media from R2: {exc}") from exc
    body = response["Body"].read()
    if not isinstance(body, (bytes, bytearray)):
        raise MediaStoreError("R2 object body was not bytes")
    total = int(response.get("ContentLength") or 0)  # may be chunk size only
    cr = response.get("ContentRange") or ""
    if "/" in cr:
        try:
            total = int(str(cr).rsplit("/", 1)[-1])
        except ValueError:
            total = head_r2_size(key, settings)
    else:
        total = head_r2_size(key, settings)
    return bytes(body), total


def store_bytes(
    *,
    content: bytes,
    subdir: str,
    filename: str,
    settings: Settings,
    content_type: str | None = None,
) -> str:
    key = media_key(subdir, filename)
    write_local_bytes(key, content, settings)
    if settings.r2_enabled:
        put_r2_bytes(key, content, settings, content_type=content_type)
    return public_url_for_key(key, settings)


def store_file(
    *,
    path: Path,
    subdir: str | None = None,
    filename: str | None = None,
    settings: Settings,
    content_type: str | None = None,
) -> str:
    if subdir is None:
        key = path.resolve().relative_to(settings.media_path.resolve()).as_posix()
    else:
        key = media_key(subdir, filename or path.name)
        target = local_path_for_key(key, settings)
        if path.resolve() != target.resolve():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
            path = target
    if settings.r2_enabled:
        put_r2_file(key, path, settings, content_type=content_type)
    return public_url_for_key(key, settings)


def _media_api_hosts(settings: Settings | None) -> set[str]:
    hosts = {"localhost", "127.0.0.1", "api.example.com"}
    raw = getattr(settings, "public_api_base_url", None) if settings else None
    if raw:
        host = (urlparse(str(raw)).hostname or "").strip().lower()
        if host:
            hosts.add(host)
    return hosts


def _assert_safe_outbound_url(url: str, settings: Settings | None = None) -> str:
    """Block private/link-local targets before server-side fetches (SSRF)."""
    from app.url_safety import UnsafeUrlError, assert_public_http_url

    # Our own signed /api/media absolute URLs are fine; skip DNS checks for same API host.
    try:
        return assert_public_http_url(url)
    except UnsafeUrlError as exc:
        parsed = urlparse(url)
        host = (parsed.hostname or "").strip().lower()
        if parsed.path.startswith("/api/media/") and host in _media_api_hosts(settings):
            return url
        raise MediaStoreError(f"Unsafe media URL: {exc}") from exc


async def download_media_url(
    *,
    url: str,
    settings: Settings,
    subdir: str,
    stem: object,
    fallback_extension: str,
    max_bytes: int = 250 * 1024 * 1024,
) -> tuple[Path, str]:
    filename = f"{safe_media_name(stem)}{extension_from_url(url, fallback_extension)}"
    key = media_key(subdir, filename)
    # Local /api/media paths: read from store instead of HTTP looping back.
    from app.media_signing import strip_media_query

    cleaned = strip_media_query(url) if url else url
    local_key = key_from_storage_url(cleaned, settings) if cleaned else None
    if local_key is not None:
        path = local_path_for_key(local_key, settings)
        if path.exists() and path.stat().st_size > 0:
            content = path.read_bytes()
            if len(content) > max_bytes:
                raise MediaStoreError("Media download exceeded the allowed size")
            out = write_local_bytes(key, content, settings)
            if settings.r2_enabled:
                put_r2_bytes(key, content, settings, content_type=content_type_for_key(key))
            return out, public_url_for_key(key, settings)
        if settings.r2_enabled:
            content = get_r2_bytes(local_key, settings)
            if len(content) > max_bytes:
                raise MediaStoreError("Media download exceeded the allowed size")
            out = write_local_bytes(key, content, settings)
            put_r2_bytes(key, content, settings, content_type=content_type_for_key(key))
            return out, public_url_for_key(key, settings)

    if url.startswith("http://") or url.startswith("https://"):
        safe_url = _assert_safe_outbound_url(url, settings)
    else:
        raise MediaStoreError("Media URL must be absolute http(s) or local /api/media storage")

    async with httpx.AsyncClient(timeout=180, follow_redirects=False) as client:
        current = safe_url
        response = None
        for _ in range(5):
            response = await client.get(current)
            if response.is_redirect:
                location = response.headers.get("location") or ""
                from app.url_safety import UnsafeUrlError, resolve_redirect

                try:
                    current = resolve_redirect(current, location)
                except UnsafeUrlError as exc:
                    raise MediaStoreError(f"Unsafe media redirect: {exc}") from exc
                continue
            break
        if response is None or response.status_code >= 400:
            code = response.status_code if response is not None else 0
            raise MediaStoreError(f"Media download failed with HTTP {code}")
        content = response.content
    if len(content) > max_bytes:
        raise MediaStoreError("Media download exceeded the allowed size")
    path = write_local_bytes(key, content, settings)
    if settings.r2_enabled:
        put_r2_bytes(key, content, settings, content_type=content_type_for_key(key))
    return path, public_url_for_key(key, settings)


def media_exists_locally(url: str, settings: Settings) -> bool:
    path = local_path_from_media_url(url, settings)
    return bool(path and path.exists() and path.stat().st_size > 0)


def ensure_local_media(url: str, settings: Settings) -> Path:
    """Resolve a storage/provider URL to a local filesystem path for FFmpeg."""
    if not url:
        raise MediaStoreError("Media URL is missing")

    key = key_from_storage_url(url, settings)
    if key is not None:
        path = local_path_for_key(key, settings)
        if path.exists() and path.stat().st_size > 0:
            return path
        if settings.r2_enabled:
            content = get_r2_bytes(key, settings)
            return write_local_bytes(key, content, settings)
        raise MediaStoreError(f"Media file is missing from local storage: {key}")

    if url.startswith("http://") or url.startswith("https://"):
        safe_url = _assert_safe_outbound_url(url, settings)
        parsed = urlparse(safe_url)
        name = safe_media_name(Path(parsed.path).stem or "remote") + extension_from_url(safe_url, ".bin")
        key = media_key("cache", name)
        path = local_path_for_key(key, settings)
        if path.exists() and path.stat().st_size > 0:
            return path
        with httpx.Client(timeout=180, follow_redirects=False) as client:
            current = safe_url
            response = None
            for _ in range(5):
                response = client.get(current)
                if response.is_redirect:
                    location = response.headers.get("location") or ""
                    from app.url_safety import UnsafeUrlError, resolve_redirect

                    try:
                        current = resolve_redirect(current, location)
                    except UnsafeUrlError as exc:
                        raise MediaStoreError(f"Unsafe media redirect: {exc}") from exc
                    continue
                break
        if response is None or response.status_code >= 400:
            code = response.status_code if response is not None else 0
            raise MediaStoreError(f"Failed to download media for local processing (HTTP {code})")
        return write_local_bytes(key, response.content, settings)

    raise MediaStoreError(f"Unsupported media URL: {url[:120]}")


async def assert_media_reachable(url: str, settings: Settings, *, label: str) -> str:
    """Ensure media is available for external providers. Returns the absolute public URL."""
    public_url = public_media_url(url, settings)
    key = key_from_storage_url(url, settings) or key_from_storage_url(public_url, settings)

    if key is not None:
        local = local_path_for_key(key, settings)
        if local.exists() and local.stat().st_size > 0:
            if settings.r2_enabled and public_url.startswith("http"):
                # Keep R2 in sync if local exists but remote may be stale/missing.
                try:
                    put_r2_file(key, local, settings, content_type=content_type_for_key(key))
                except MediaStoreError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise MediaStoreError(f"{label} could not be uploaded to R2: {exc}") from exc
            return public_url
        if settings.r2_enabled:
            try:
                client = r2_client(settings)
                client.head_object(Bucket=settings.r2_bucket_name, Key=key)
                return public_url
            except MediaStoreError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise MediaStoreError(f"{label} is missing from R2 storage ({key}): {exc}") from exc
        raise MediaStoreError(f"{label} file is missing from local media storage ({key}). Regenerate or re-upload it.")

    if public_url.startswith("http://") or public_url.startswith("https://"):
        safe_url = _assert_safe_outbound_url(public_url, settings)
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            try:
                current = safe_url
                head = None
                for _ in range(5):
                    head = await client.head(current)
                    if head.is_redirect:
                        location = head.headers.get("location") or ""
                        from app.url_safety import UnsafeUrlError, resolve_redirect

                        try:
                            current = resolve_redirect(current, location)
                        except UnsafeUrlError as exc:
                            raise MediaStoreError(f"{label} redirect is not safe: {exc}") from exc
                        continue
                    break
                if head is not None and head.status_code < 400:
                    return public_url
                get = await client.get(current, headers={"Range": "bytes=0-0"})
            except httpx.HTTPError as exc:
                raise MediaStoreError(f"{label} URL is not reachable: {exc}") from exc
        if get.status_code >= 400:
            raise MediaStoreError(f"{label} URL returned HTTP {get.status_code}")
        return public_url

    raise MediaStoreError(f"{label} URL is not publicly reachable: {public_url}")
