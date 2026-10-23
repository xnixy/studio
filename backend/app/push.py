"""Expo push delivery (best-effort, never raises to callers)."""

from __future__ import annotations

import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.devices import DevicePushToken

logger = logging.getLogger("studio.push")

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Expo rejects a whole request whose messages span more than one experience id.
# One user can easily hold a mixed set (store build alongside a dev client, or a
# slug rename), and the rejection takes down every device in the batch, not just
# the odd one out.
_TOO_MANY_EXPERIENCES = "PUSH_TOO_MANY_EXPERIENCE_IDS"


def _messages_for(tokens: list[str], *, title: str, body: str | None, data: dict | None) -> list[dict]:
    return [
        {
            "to": t,
            "title": title,
            "body": body or "",
            "sound": "default",
            "data": data or {},
        }
        for t in tokens
    ]


def _conflict_error(payload: object) -> dict | None:
    """The experience-conflict error object, if that is what Expo returned."""
    if not isinstance(payload, dict):
        return None
    errors = payload.get("errors")
    if not isinstance(errors, list):
        return None
    for err in errors:
        if isinstance(err, dict) and err.get("code") == _TOO_MANY_EXPERIENCES:
            return err
    return None


def _experience_groups(payload: object, sent: list[str]) -> list[list[str]] | None:
    """Token groups from an Expo conflict body, or None if they are unusable.

    The error carries ``details`` as {experience_id: [token, ...]} — the exact
    split Expo wants, so we regroup from its own answer rather than guessing.
    """
    err = _conflict_error(payload)
    if err is None:
        return None
    details = err.get("details")
    if not isinstance(details, dict):
        return None
    known = set(sent)
    groups = [
        [t for t in group if t in known] for group in details.values() if isinstance(group, list)
    ]
    groups = [g for g in groups if g]
    if not groups:
        return None
    # A token Expo did not attribute to any experience still deserves a send.
    grouped = {t for g in groups for t in g}
    leftover = [t for t in sent if t not in grouped]
    return groups + [[t] for t in leftover]


def _dead_tokens(payload: object, sent: list[str]) -> list[str]:
    """Tokens Expo reports as gone. Tickets are order-matched to the messages sent."""
    if not isinstance(payload, dict):
        return []
    tickets = payload.get("data")
    if not isinstance(tickets, list):
        return []
    dead: list[str] = []
    for token, ticket in zip(sent, tickets):
        if not isinstance(ticket, dict) or ticket.get("status") != "error":
            continue
        details = ticket.get("details")
        if isinstance(details, dict) and details.get("error") == "DeviceNotRegistered":
            dead.append(token)
    return dead


async def _forget_tokens(tokens: list[str]) -> None:
    """Drop tokens Expo says are dead, on a session of our own.

    Never the caller's session: ``emit`` may still be mid-transaction, and
    committing here would commit its uncommitted work along with the delete.
    """
    if not tokens:
        return
    from app.database import SessionLocal

    try:
        async with SessionLocal() as session:
            rows = (
                await session.scalars(select(DevicePushToken).where(DevicePushToken.token.in_(tokens)))
            ).all()
            for row in rows:
                await session.delete(row)
            if rows:
                await session.commit()
                logger.info("dropped %s unregistered push token(s)", len(rows))
    except Exception:
        logger.exception("push token cleanup failed")


async def _post(
    client: httpx.AsyncClient,
    tokens: list[str],
    *,
    title: str,
    body: str | None,
    data: dict | None,
) -> tuple[int, object]:
    resp = await client.post(EXPO_PUSH_URL, json=_messages_for(tokens, title=title, body=body, data=data))
    try:
        payload: object = resp.json()
    except Exception:
        payload = None
    if resp.status_code >= 400:
        logger.warning("expo push failed status=%s body=%s", resp.status_code, resp.text[:300])
    return resp.status_code, payload


async def send_expo_push_to_user(
    session: AsyncSession,
    *,
    user_id: UUID,
    title: str,
    body: str | None = None,
    data: dict | None = None,
) -> None:
    try:
        tokens = list(
            (
                await session.scalars(
                    select(DevicePushToken.token).where(DevicePushToken.user_id == user_id)
                )
            ).all()
        )
        if not tokens:
            return

        dead: list[str] = []
        async with httpx.AsyncClient(timeout=12.0) as client:
            status, payload = await _post(client, tokens, title=title, body=body, data=data)
            if status < 400:
                dead = _dead_tokens(payload, tokens)
            elif _conflict_error(payload) is not None:
                # Split once, off Expo's own grouping. No recursion: a group that
                # still conflicts is a bug we want in the logs, not a retry loop.
                # Any other 400 is already logged and is not helped by resending.
                groups = _experience_groups(payload, tokens)
                if groups is None:
                    # Conflict with unusable details. One message per request cannot
                    # span experiences by construction, and this is a per-user send
                    # (a handful of devices), so the cost is bounded.
                    groups = [[t] for t in tokens]
                for group in groups:
                    group_status, group_payload = await _post(
                        client, group, title=title, body=body, data=data
                    )
                    if group_status < 400:
                        dead.extend(_dead_tokens(group_payload, group))

        await _forget_tokens(dead)
    except Exception:
        logger.exception("expo push failed user=%s", user_id)
