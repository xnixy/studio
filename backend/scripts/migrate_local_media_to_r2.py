"""Upload legacy /api/media/* objects to R2 and rewrite DB URLs.

Run from backend/:
  .venv/Scripts/python.exe scripts/migrate_local_media_to_r2.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.media_store import (  # noqa: E402
    content_type_for_key,
    key_from_storage_url,
    local_path_for_key,
    public_url_for_key,
    put_r2_file,
    r2_client,
)
from app.models import CaptionTrack, VideoAsset, VideoRender, VoiceoverAsset  # noqa: E402


def needs_migrate(url: str | None) -> bool:
    return bool(url and url.startswith("/api/media/"))


async def ensure_on_r2(url: str, settings, client, stats: dict) -> str:
    key = key_from_storage_url(url, settings)
    if not key:
        stats["errors"] += 1
        return url
    public = public_url_for_key(key, settings)
    try:
        client.head_object(Bucket=settings.r2_bucket_name, Key=key)
        stats["already_remote"] += 1
        return public
    except Exception:
        pass
    local = local_path_for_key(key, settings)
    if local.exists() and local.stat().st_size > 0:
        put_r2_file(key, local, settings, content_type=content_type_for_key(key))
        stats["uploaded"] += 1
        print(f"  uploaded {key} ({local.stat().st_size} bytes)")
        return public
    stats["missing_local"] += 1
    print(f"  MISSING {key}")
    return url


async def main() -> int:
    settings = get_settings()
    if not settings.r2_enabled:
        print("R2 is not fully configured")
        return 1
    client = r2_client(settings)
    stats = {"uploaded": 0, "already_remote": 0, "missing_local": 0, "updated_db": 0, "errors": 0}

    async with SessionLocal() as session:
        assets = list((await session.execute(select(VideoAsset))).scalars())
        voiceovers = list((await session.execute(select(VoiceoverAsset))).scalars())
        renders = list((await session.execute(select(VideoRender))).scalars())
        captions = list((await session.execute(select(CaptionTrack))).scalars())

        for asset in assets:
            for field in ("storage_url", "provider_url"):
                old = getattr(asset, field)
                if needs_migrate(old):
                    new = await ensure_on_r2(old, settings, client, stats)
                    if new != old:
                        setattr(asset, field, new)
                        stats["updated_db"] += 1
            meta = dict(asset.asset_metadata or {})
            if isinstance(meta.get("public_url"), str) and needs_migrate(meta["public_url"]):
                meta["public_url"] = await ensure_on_r2(meta["public_url"], settings, client, stats)
                asset.asset_metadata = meta
                stats["updated_db"] += 1

        for row in voiceovers:
            if needs_migrate(row.download_url):
                new = await ensure_on_r2(row.download_url, settings, client, stats)
                if new != row.download_url:
                    row.download_url = new
                    stats["updated_db"] += 1

        for row in renders:
            if needs_migrate(row.output_url):
                new = await ensure_on_r2(row.output_url, settings, client, stats)
                if new != row.output_url:
                    row.output_url = new
                    stats["updated_db"] += 1
            meta = dict(row.render_metadata or {})
            changed = False
            for key, value in list(meta.items()):
                if isinstance(value, str) and needs_migrate(value):
                    meta[key] = await ensure_on_r2(value, settings, client, stats)
                    changed = True
            if changed:
                row.render_metadata = meta
                stats["updated_db"] += 1

        for row in captions:
            for field in ("vtt_url", "srt_url", "storage_url", "url", "file_url"):
                if hasattr(row, field) and needs_migrate(getattr(row, field)):
                    new = await ensure_on_r2(getattr(row, field), settings, client, stats)
                    if new != getattr(row, field):
                        setattr(row, field, new)
                        stats["updated_db"] += 1

        await session.commit()

    print("done", stats)
    return 0 if stats["missing_local"] == 0 and stats["errors"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
