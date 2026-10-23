"""Emit domain events into durable inbox + live channel."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events.catalog import job_notification_spec
from app.events.hub import event_hub
from app.models import Notification, NotificationPreference, User, WorkspaceMember

logger = logging.getLogger(__name__)

RecipientMode = Literal["actor_only", "workspace_members", "user_ids", "workspace_admins"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _recipient_ids(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    recipient_mode: str,
    actor_user_id: UUID | None,
    user_ids: list[UUID] | None,
) -> list[UUID]:
    if recipient_mode == "user_ids":
        return list({uid for uid in (user_ids or []) if uid is not None})
    if recipient_mode == "actor_only":
        return [actor_user_id] if actor_user_id else []

    roles: tuple[str, ...] | None = None
    if recipient_mode == "workspace_admins":
        roles = ("owner", "admin")

    query = select(WorkspaceMember.user_id).where(WorkspaceMember.workspace_id == workspace_id)
    if roles is not None:
        query = query.where(WorkspaceMember.role.in_(roles))
    member_ids = list((await session.scalars(query)).all())
    if not member_ids:
        return []
    active = (
        await session.scalars(
            select(User.id).where(User.id.in_(member_ids), User.is_disabled.is_(False))
        )
    ).all()
    return list(active)


async def _prefs_for(
    session: AsyncSession,
    *,
    user_id: UUID,
    workspace_id: UUID,
    event_type: str,
) -> tuple[bool, bool, bool]:
    """Return (in_app, email, toast). Defaults all in_app+toast on, email off."""
    rows = (
        await session.scalars(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user_id,
                (NotificationPreference.workspace_id == workspace_id)
                | (NotificationPreference.workspace_id.is_(None)),
            )
        )
    ).all()
    if not rows:
        return True, False, True

    def score(p: NotificationPreference) -> int:
        s = 0
        if p.workspace_id is not None:
            s += 2
        if p.event_type == event_type:
            s += 4
        elif p.event_type == "*":
            s += 1
        else:
            return -1
        return s

    best: NotificationPreference | None = None
    best_score = -1
    for p in rows:
        sc = score(p)
        if sc > best_score:
            best_score = sc
            best = p
    if best is None or best_score < 0:
        return True, False, True
    return bool(best.in_app), bool(best.email), bool(best.toast)


async def emit_domain_event(
    session: AsyncSession,
    *,
    type: str,
    workspace_id: UUID,
    actor_user_id: UUID | None = None,
    entity_kind: str | None = None,
    entity_id: UUID | None = None,
    title: str | None = None,
    body: str | None = None,
    href: str | None = None,
    payload: dict[str, Any] | None = None,
    recipient_mode: RecipientMode | str = "workspace_members",
    user_ids: list[UUID] | None = None,
    persist: bool = True,
    live: bool = True,
    toast: bool = True,
    dedupe_key: str | None = None,
    commit: bool = False,
) -> dict[str, Any] | None:
    """Create inbox rows and/or publish a live event. Never raises to callers."""
    try:
        event_id = uuid.uuid4()
        occurred_at = _utcnow()
        title_s = (title or type)[:200]
        body_s = body
        href_s = (href or None)
        payload_s = dict(payload or {})
        asset_id = payload_s.get("asset_id") or (str(entity_id) if entity_id else None)

        recipients: list[UUID] = []
        if persist:
            recipients = await _recipient_ids(
                session,
                workspace_id=workspace_id,
                recipient_mode=str(recipient_mode),
                actor_user_id=actor_user_id,
                user_ids=user_ids,
            )

        created_for: list[str] = []
        for uid in recipients:
            in_app, _email, toast_pref = await _prefs_for(
                session, user_id=uid, workspace_id=workspace_id, event_type=type
            )
            if not in_app:
                continue
            user_toast = toast and toast_pref
            row = Notification(
                id=uuid.uuid4() if len(recipients) > 1 else event_id,
                workspace_id=workspace_id,
                user_id=uid,
                type=type[:80],
                title=title_s,
                body=body_s,
                href=href_s[:500] if href_s else None,
                entity_kind=entity_kind,
                entity_id=entity_id,
                payload={**payload_s, "toast": user_toast},
                dedupe_key=dedupe_key[:160] if dedupe_key else None,
            )
            try:
                async with session.begin_nested():
                    session.add(row)
                    await session.flush()
                created_for.append(str(uid))
            except Exception:
                # Dedupe unique violation or flush error — skip this recipient
                logger.debug("notification insert skipped type=%s user=%s", type, uid, exc_info=True)

        if commit:
            await session.commit()

        # Mobile push (best-effort; does not block domain event).
        if persist and created_for and title_s:
            try:
                from app.push import send_expo_push_to_user
                from uuid import UUID as _UUID

                for uid_s in created_for:
                    await send_expo_push_to_user(
                        session,
                        user_id=_UUID(uid_s),
                        title=title_s,
                        body=body_s,
                        data={
                            k: v
                            for k, v in {
                                "href": href_s,
                                "type": type,
                                "asset_id": str(asset_id) if asset_id else None,
                            }.items()
                            if v
                        },
                    )
            except Exception:
                logger.debug("push fanout skipped", exc_info=True)

        envelope: dict[str, Any] = {
            "v": 1,
            "id": str(event_id),
            "type": type,
            "workspace_id": str(workspace_id),
            "occurred_at": occurred_at.isoformat(),
            "actor_user_id": str(actor_user_id) if actor_user_id else None,
            "entity": {"kind": entity_kind, "id": str(entity_id) if entity_id else None},
            "payload": {
                "title": title_s,
                "body": body_s,
                "href": href_s,
                "extra": payload_s,
            },
            "delivery": {
                "persist": persist,
                "live": live,
                "toast": toast,
                "recipient_mode": recipient_mode,
                "recipient_user_ids": created_for if persist else [str(u) for u in (user_ids or [])],
            },
        }

        if live:
            try:
                await event_hub.publish(envelope)
            except Exception:
                logger.exception("live publish failed type=%s", type)

        return envelope
    except Exception:
        logger.exception("emit_domain_event failed type=%s workspace=%s", type, workspace_id)
        return None


async def emit_job_terminal(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    job_id: UUID,
    job_type: str,
    status: str,
    created_by_id: UUID | None = None,
    error_message: str | None = None,
    result: dict[str, Any] | None = None,
    commit: bool = False,
) -> None:
    spec = job_notification_spec(
        job_type,
        status,
        job_id=job_id,
        error_message=error_message,
        result=result,
    )
    if not spec:
        return
    await emit_domain_event(
        session,
        type=spec["type"],
        workspace_id=workspace_id,
        actor_user_id=created_by_id,
        entity_kind=spec.get("entity_kind"),
        entity_id=spec.get("entity_id"),
        title=spec.get("title"),
        body=spec.get("body"),
        href=spec.get("href"),
        payload=spec.get("payload"),
        recipient_mode=spec.get("recipient_mode") or "workspace_members",
        persist=bool(spec.get("persist", True)),
        live=bool(spec.get("live", True)),
        toast=bool(spec.get("toast", True)),
        dedupe_key=spec.get("dedupe_key"),
        commit=commit,
    )
