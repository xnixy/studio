#!/usr/bin/env python3
"""Restore Faces deleted by the first cut of 0043.

0043 meant to drop leftover xAI talking clips. Faces are the same table with
play_mode=avatar and no voice, so the empty-voice clause deleted them. Files
under avatar-assets/ were not removed.

Usage (from backend/):
  uv run python scripts/restore_purged_faces.py --dry-run
  uv run python scripts/restore_purged_faces.py
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import SessionLocal
from app.media_store import public_url_for_key, r2_client, r2_enabled
from app.models import User, VideoAsset, VideoProject, Workspace
from app.models.agency import AuditEvent
from app.routers.play_helpers import PLAY_PROJECT_TITLE, get_or_create_play_project

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.I,
)
_STARTER_RE = re.compile(
    r"^(?P<project>[0-9a-f-]{36})-starter-(?P<name>[a-z]+)-[0-9a-f]+$",
    re.I,
)
_UPLOAD_RE = re.compile(
    r"^(?P<project>[0-9a-f-]{36})-(?P<rand>[0-9a-f]{8,12})$",
    re.I,
)
_MIN_BYTES = 1000
_CREATE_ACTIONS = {
    "play.face_generated",
    "play.avatar_image_uploaded",
    "play.face_from_starter",
    "play.face_edited",
}


@dataclass(frozen=True)
class StoredFace:
    key: str
    size: int
    modified: datetime
    stem: str


def _parse_uuid(raw: object) -> uuid.UUID | None:
    text = str(raw or "").strip()
    if not text or text.lower() in {"none", "null"}:
        return None
    try:
        return uuid.UUID(text)
    except ValueError:
        return None


def _label_for_starter(name: str) -> str:
    return name.strip().capitalize() or "Face"


def _list_avatar_files(settings) -> list[StoredFace]:
    rows: list[StoredFace] = []
    if r2_enabled(settings):
        client = r2_client(settings)
        paginator = client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=settings.r2_bucket_name, Prefix="avatar-assets/"):
            for obj in page.get("Contents") or []:
                key = str(obj.get("Key") or "")
                size = int(obj.get("Size") or 0)
                modified = obj.get("LastModified")
                if not key or size < _MIN_BYTES:
                    continue
                stem = Path(key).stem
                when = modified if isinstance(modified, datetime) else datetime.now(timezone.utc)
                rows.append(StoredFace(key=key, size=size, modified=when, stem=stem))
        return rows
    folder = settings.media_path / "avatar-assets"
    if not folder.is_dir():
        return rows
    for path in folder.iterdir():
        if not path.is_file() or path.stat().st_size < _MIN_BYTES:
            continue
        stat = path.stat()
        when = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        rows.append(
            StoredFace(
                key=f"avatar-assets/{path.name}",
                size=stat.st_size,
                modified=when,
                stem=path.stem,
            )
        )
    return rows


async def _load_workspace_user(session: AsyncSession, workspace_id: uuid.UUID) -> User:
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise SystemExit(f"workspace {workspace_id} is gone")
    user = await session.get(User, workspace.created_by_id)
    if user is None:
        raise SystemExit(f"workspace {workspace_id} has no owner")
    return user


def _audit_asset_id(details: dict) -> uuid.UUID | None:
    return _parse_uuid(details.get("asset_id")) or _parse_uuid(details.get("face_id"))


async def restore(*, dry_run: bool) -> int:
    settings = get_settings()
    files = _list_avatar_files(settings)
    created = 0
    skipped = 0
    async with SessionLocal() as session:
        existing_ids = set(
            (await session.scalars(select(VideoAsset.id))).all()
        )
        existing_urls = {
            str(url)
            for url in (await session.scalars(select(VideoAsset.storage_url))).all()
            if url
        }
        projects = (
            await session.scalars(select(VideoProject).where(VideoProject.title == PLAY_PROJECT_TITLE))
        ).all()
        project_ws = {p.id: p.workspace_id for p in projects}

        audits = (
            await session.scalars(
                select(AuditEvent)
                .where(AuditEvent.action.in_({*_CREATE_ACTIONS, "play.face_deleted"}))
                .order_by(AuditEvent.created_at)
            )
        ).all()
        deleted: set[uuid.UUID] = set()
        generated_ws: dict[uuid.UUID, uuid.UUID] = {}
        for event in audits:
            details = dict(event.details or {})
            asset_id = _audit_asset_id(details)
            if event.action == "play.face_deleted" and asset_id is not None:
                deleted.add(asset_id)
                continue
            if asset_id is not None and event.action == "play.face_generated":
                generated_ws[asset_id] = event.workspace_id

        # Latest starter copy per Play project.
        starters: dict[tuple[uuid.UUID, str], StoredFace] = {}
        uploads: list[StoredFace] = []
        generated: list[StoredFace] = []
        leftover: list[StoredFace] = []
        for stored in files:
            starter = _STARTER_RE.match(stored.stem)
            upload = _UPLOAD_RE.match(stored.stem)
            if starter:
                project_id = uuid.UUID(starter.group("project"))
                name = starter.group("name").lower()
                key = (project_id, name)
                prev = starters.get(key)
                if prev is None or stored.modified >= prev.modified:
                    starters[key] = stored
                continue
            if upload and stored.stem.split("-")[0:5]:
                uploads.append(stored)
                continue
            if _UUID_RE.fullmatch(stored.stem):
                generated.append(stored)
                continue
            leftover.append(stored)

        planned: list[tuple[uuid.UUID, uuid.UUID, StoredFace, dict]] = []

        def queue(
            *,
            asset_id: uuid.UUID,
            workspace_id: uuid.UUID,
            stored: StoredFace,
            meta: dict,
            source: str,
            prompt: str,
        ) -> None:
            url = public_url_for_key(stored.key, settings)
            if asset_id in existing_ids or asset_id in deleted or url in existing_urls:
                return
            planned.append(
                (
                    asset_id,
                    workspace_id,
                    stored,
                    {
                        "source": source,
                        "prompt": prompt,
                        "url": url,
                        "meta": meta,
                    },
                )
            )

        for stored in generated:
            asset_id = uuid.UUID(stored.stem)
            workspace_id = generated_ws.get(asset_id)
            if workspace_id is None:
                # Orphan generate/edit stills: attach to the Play project owner
                # if the filename is only a uuid (no project prefix).
                if len(project_ws) == 1:
                    workspace_id = next(iter(project_ws.values()))
                else:
                    # Nick's original workspace is the one with generated audits.
                    workspace_id = next(iter(generated_ws.values()), None)
                    if workspace_id is None and project_ws:
                        workspace_id = next(iter(project_ws.values()))
            if workspace_id is None:
                continue
            queue(
                asset_id=asset_id,
                workspace_id=workspace_id,
                stored=stored,
                source="xai",
                prompt="Play avatar face generate",
                meta={
                    "play": True,
                    "play_mode": "avatar",
                    "mode": "avatar_source_image",
                    "face_library": True,
                    "source_kind": "generated",
                    "label": "Generated face",
                    "consent_confirmed": True,
                    "restored_from_purge": True,
                    "storage_backend": "r2" if r2_enabled(settings) else "local",
                },
            )

        for stored in uploads:
            match = _UPLOAD_RE.match(stored.stem)
            if match is None:
                continue
            project_id = uuid.UUID(match.group("project"))
            workspace_id = project_ws.get(project_id)
            if workspace_id is None:
                leftover.append(stored)
                continue
            queue(
                asset_id=uuid.uuid4(),
                workspace_id=workspace_id,
                stored=stored,
                source="upload",
                prompt="Play avatar face upload",
                meta={
                    "play": True,
                    "play_mode": "avatar",
                    "play_platform": "tiktok",
                    "mode": "avatar_source_image",
                    "face_library": True,
                    "source_kind": "upload",
                    "label": "Uploaded face",
                    "consent_confirmed": True,
                    "restored_from_purge": True,
                    "storage_backend": "r2" if r2_enabled(settings) else "local",
                },
            )

        for (project_id, name), stored in starters.items():
            workspace_id = project_ws.get(project_id)
            if workspace_id is None:
                leftover.append(stored)
                continue
            label = _label_for_starter(name)
            queue(
                asset_id=uuid.uuid4(),
                workspace_id=workspace_id,
                stored=stored,
                source="upload",
                prompt="Play avatar face",
                meta={
                    "play": True,
                    "play_mode": "avatar",
                    "play_platform": "tiktok",
                    "mode": "avatar_source_image",
                    "face_library": True,
                    "source_kind": "starter",
                    "label": label,
                    "consent_confirmed": True,
                    "restored_from_purge": True,
                    "storage_backend": "r2" if r2_enabled(settings) else "local",
                },
            )

        # Old uploads whose Play project row is gone: put on the workspace that
        # already owns generated faces when we can; otherwise skip.
        fallback_ws = next(iter(generated_ws.values()), None)
        for stored in leftover:
            if fallback_ws is None:
                continue
            kind = "upload"
            source = "upload"
            label = "Uploaded face"
            prompt = "Play avatar face upload"
            asset_id = uuid.uuid4()
            if _UUID_RE.fullmatch(stored.stem):
                kind = "generated"
                source = "xai"
                label = "Generated face"
                prompt = "Play avatar face generate"
                asset_id = uuid.UUID(stored.stem)
            queue(
                asset_id=asset_id,
                workspace_id=fallback_ws,
                stored=stored,
                source=source,
                prompt=prompt,
                meta={
                    "play": True,
                    "play_mode": "avatar",
                    "mode": "avatar_source_image",
                    "face_library": True,
                    "source_kind": kind,
                    "label": label,
                    "consent_confirmed": True,
                    "restored_from_purge": True,
                    "storage_backend": "r2" if r2_enabled(settings) else "local",
                },
            )

        print(f"files={len(files)} planned={len(planned)} dry_run={dry_run}")
        seen_urls: set[str] = set()
        for asset_id, workspace_id, stored, payload in planned:
            url = payload["url"]
            if url in seen_urls:
                skipped += 1
                continue
            seen_urls.add(url)
            print(f"  restore {asset_id} ws={workspace_id} {stored.key} {payload['meta'].get('label')}")
            if dry_run:
                created += 1
                continue
            user = await _load_workspace_user(session, workspace_id)
            project = await get_or_create_play_project(
                session, workspace_id=workspace_id, user=user, platform_key="tiktok"
            )
            meta = dict(payload["meta"])
            meta["public_url"] = url
            session.add(
                VideoAsset(
                    id=asset_id,
                    workspace_id=workspace_id,
                    video_project_id=project.id,
                    video_scene_id=None,
                    asset_type="image",
                    source=payload["source"],
                    status="ready",
                    prompt=payload["prompt"],
                    provider="user_upload" if payload["source"] == "upload" else payload["source"],
                    storage_url=url,
                    asset_metadata=meta,
                    created_at=stored.modified,
                    updated_at=stored.modified,
                )
            )
            existing_ids.add(asset_id)
            existing_urls.add(url)
            created += 1

        if not dry_run:
            await session.commit()
        print(f"restored={created} skipped={skipped}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return asyncio.run(restore(dry_run=args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
