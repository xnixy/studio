"""Authenticated media serving — private objects only via signature or workspace ACL."""

from __future__ import annotations

import re
from pathlib import Path
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.media_signing import verify_media_signature
from app.media_store import (
    MediaStoreError,
    content_type_for_key,
    get_r2_bytes,
    get_r2_bytes_range,
    head_r2_size,
    is_public_marketing_key,
    local_path_for_key,
    r2_enabled,
)
from app.models import User, VideoAsset, VideoRender
from app.security import decode_access_token, parse_user_id
from app.workspace_access import require_permission

router = APIRouter(tags=["media"])

_RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)", re.IGNORECASE)


def _parse_bytes_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Parse Range into inclusive (start, end), or None for full body. Single ranges only."""
    if not header or size <= 0:
        return None
    raw = header.strip().split(",", 1)[0].strip()
    match = _RANGE_RE.fullmatch(raw)
    if not match:
        return None
    start_s, end_s = match.group(1), match.group(2)
    if start_s == "" and end_s == "":
        return None
    if start_s == "":
        length = int(end_s)
        if length <= 0:
            return None
        start = max(0, size - length)
        end = size - 1
    else:
        start = int(start_s)
        end = int(end_s) if end_s != "" else size - 1
    if start >= size:
        return None
    end = min(end, size - 1)
    if end < start:
        return None
    return start, end


def _bearer_user_id(request: Request, settings: Settings) -> UUID | None:
    auth = request.headers.get("authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    if not token or token.startswith("studio_"):
        return None
    try:
        payload = decode_access_token(token, settings)
    except jwt.PyJWTError:
        return None
    return parse_user_id(payload.get("sub"))


def _url_matches_media_key(url: str | None, key: str) -> bool:
    """True when a stored URL points at this media key (exact path, not substring)."""
    if not url or not key:
        return False
    from app.config import get_settings
    from app.media_signing import strip_media_query
    from app.media_store import key_from_storage_url

    cleaned = strip_media_query(url).split("?", 1)[0]
    marker = f"/api/media/{key}"
    if cleaned == marker or cleaned.endswith(marker):
        # Ensure we matched the full key, not a longer suffix collision
        if cleaned == marker or cleaned.endswith("/" + key) or cleaned.endswith(marker):
            idx = cleaned.rfind("/api/media/")
            if idx >= 0 and cleaned[idx + len("/api/media/") :] == key:
                return True
    extracted = key_from_storage_url(cleaned, get_settings())
    return extracted == key


async def _user_can_access_key(session: AsyncSession, user: User, key: str) -> bool:
    # Prefer structured workspace path: workspaces/{uuid}/...
    parts = key.split("/")
    if len(parts) >= 2 and parts[0] == "workspaces":
        try:
            workspace_id = UUID(parts[1])
        except ValueError:
            workspace_id = None
        if workspace_id is not None:
            try:
                await require_permission(session, workspace_id, user, "projects.read")
                return True
            except HTTPException:
                return False

    # Clip stills: play/{asset_id}-poster.jpg (stored only in metadata, not storage_url).
    if len(parts) == 2 and parts[0] == "play" and parts[1].endswith("-poster.jpg"):
        stem = parts[1][: -len("-poster.jpg")]
        try:
            asset_id = UUID(stem)
        except ValueError:
            asset_id = None
        if asset_id is not None:
            asset = await session.get(VideoAsset, asset_id)
            if asset is not None and asset.workspace_id is not None:
                try:
                    await require_permission(session, asset.workspace_id, user, "projects.read")
                    return True
                except HTTPException:
                    return False

    # Exact key match via URL suffix (not SQL contains substring).
    suffix = f"/api/media/{key}"
    assets = (
        await session.scalars(
            select(VideoAsset)
            .where(
                or_(
                    VideoAsset.storage_url.endswith(suffix),
                    VideoAsset.storage_url == suffix,
                    VideoAsset.provider_url.endswith(suffix),
                )
            )
            .limit(20)
        )
    ).all()
    workspace_ids: set[UUID] = set()
    for asset in assets:
        if _url_matches_media_key(asset.storage_url, key) or _url_matches_media_key(asset.provider_url, key):
            if asset.workspace_id:
                workspace_ids.add(asset.workspace_id)

    renders = (
        await session.scalars(
            select(VideoRender)
            .where(
                or_(
                    VideoRender.output_url.endswith(suffix),
                    VideoRender.output_url == suffix,
                )
            )
            .limit(20)
        )
    ).all()
    for render in renders:
        if _url_matches_media_key(render.output_url, key) and render.workspace_id:
            workspace_ids.add(render.workspace_id)

    if not workspace_ids:
        return False

    for workspace_id in workspace_ids:
        try:
            await require_permission(session, workspace_id, user, "projects.read")
            return True
        except HTTPException:
            continue
    return False


async def _authorized_for_media(
    request: Request,
    settings: Settings,
    session: AsyncSession,
    *,
    key: str,
    exp: str | None,
    sig: str | None,
) -> bool:
    if is_public_marketing_key(key):
        return True
    if verify_media_signature(key, exp, sig, settings):
        return True

    user_id = _bearer_user_id(request, settings)
    if user_id is None:
        return False
    user = await session.get(User, user_id)
    if user is None or getattr(user, "is_disabled", False):
        return False
    return await _user_can_access_key(session, user, key)


def _media_common_headers(key: str, media_type: str, *, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Headers AVPlayer expects for progressive MP4 (inline + Accept-Ranges)."""
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": media_type,
        "Content-Disposition": f'inline; filename="{Path(key).name}"',
        "Cache-Control": "private, max-age=300",
        # Avoid intermediary transforms that break byte ranges.
        "X-Content-Type-Options": "nosniff",
    }
    if extra:
        headers.update(extra)
    return headers


@router.api_route("/media/{file_path:path}", methods=["GET", "HEAD"])
async def serve_media(
    file_path: str,
    request: Request,
    exp: str | None = Query(default=None),
    sig: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    """Serve private media with HTTP Range (required for iOS AVPlayer streaming).

    HEAD is supported explicitly so players can probe size/type before Range GETs.
    """
    key = "/".join(part for part in Path(file_path).as_posix().split("/") if part not in {"", ".", ".."})
    if not key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")

    if not await _authorized_for_media(request, settings, session, key=key, exp=exp, sig=sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Media authentication required")

    media_type = content_type_for_key(key)
    range_header = request.headers.get("range") or request.headers.get("Range")
    is_head = request.method.upper() == "HEAD"

    # Local disk: FileResponse supports Range natively on GET.
    try:
        path = local_path_for_key(key, settings)
        media_root = settings.media_path.resolve()
        resolved = path.resolve()
        resolved.relative_to(media_root)
        if resolved.is_file():
            size = resolved.stat().st_size
            if is_head:
                return Response(
                    status_code=status.HTTP_200_OK,
                    headers=_media_common_headers(
                        key,
                        media_type,
                        extra={"Content-Length": str(size)},
                    ),
                )
            resp = FileResponse(
                resolved,
                media_type=media_type,
                filename=resolved.name,
                content_disposition_type="inline",
            )
            # Starlette sets Range on GET; ensure Accept-Ranges is always present.
            resp.headers.setdefault("Accept-Ranges", "bytes")
            resp.headers.setdefault("Cache-Control", "private, max-age=300")
            return resp
    except (MediaStoreError, OSError, ValueError):
        pass

    if r2_enabled(settings):
        try:
            size = head_r2_size(key, settings)
        except MediaStoreError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found") from None

        if is_head:
            return Response(
                status_code=status.HTTP_200_OK,
                headers=_media_common_headers(
                    key,
                    media_type,
                    extra={"Content-Length": str(size)},
                ),
            )

        byte_range = _parse_bytes_range(range_header, size) if size > 0 else None
        if range_header and size > 0 and byte_range is None:
            # Only 416 when the start is past EOF (AVPlayer probe). Malformed → full body.
            raw = range_header.strip().split(",", 1)[0].strip()
            match = _RANGE_RE.fullmatch(raw)
            if match and match.group(1) != "":
                try:
                    if int(match.group(1)) >= size:
                        return Response(
                            status_code=status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE,
                            headers={
                                "Content-Range": f"bytes */{size}",
                                "Accept-Ranges": "bytes",
                            },
                        )
                except ValueError:
                    pass
        if byte_range is not None:
            start, end = byte_range
            try:
                chunk, total = get_r2_bytes_range(key, settings, start=start, end=end)
            except MediaStoreError:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found") from None
            return Response(
                content=chunk,
                status_code=status.HTTP_206_PARTIAL_CONTENT,
                media_type=media_type,
                headers=_media_common_headers(
                    key,
                    media_type,
                    extra={
                        "Content-Range": f"bytes {start}-{end}/{total}",
                        "Content-Length": str(len(chunk)),
                    },
                ),
            )

        try:
            body = get_r2_bytes(key, settings)
        except MediaStoreError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found") from None
        return Response(
            content=body,
            media_type=media_type,
            headers=_media_common_headers(
                key,
                media_type,
                extra={"Content-Length": str(len(body))},
            ),
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media not found")
