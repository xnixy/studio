"""Helpers for best-effort transactional email and recipient resolution."""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.email_delivery import EmailDeliveryError, email_delivery_configured, send_email
from app.models import User, Workspace, WorkspaceMember

logger = logging.getLogger(__name__)


async def safe_send_email(
    subject: str,
    body: str,
    recipients: list[str] | str | None,
    settings: Settings,
) -> tuple[bool, str | None]:
    """Send email without raising. Returns (sent, error_message)."""
    if isinstance(recipients, str):
        cleaned = [recipients.strip()] if recipients and recipients.strip() else []
    else:
        cleaned = [r.strip() for r in (recipients or []) if r and str(r).strip()]
    # de-dupe preserve order
    seen: set[str] = set()
    unique: list[str] = []
    for email in cleaned:
        key = email.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(email)
    if not unique:
        return False, "No recipients"
    if not email_delivery_configured(settings):
        return False, "Email delivery is not configured"
    try:
        await send_email(subject, body, unique, settings)
        return True, None
    except EmailDeliveryError as exc:
        logger.warning("email send failed subject=%r recipients=%s: %s", subject, unique, exc)
        return False, str(exc)


async def emails_for_user_ids(session: AsyncSession, user_ids: list[UUID | None]) -> list[str]:
    ids = [uid for uid in user_ids if uid is not None]
    if not ids:
        return []
    users = (await session.scalars(select(User).where(User.id.in_(ids), User.is_disabled.is_(False)))).all()
    return [u.email for u in users if u.email]


async def workspace_admin_emails(session: AsyncSession, workspace_id: UUID) -> list[str]:
    """Owner + admin emails for billing and ops-style workspace notices."""
    members = (
        await session.scalars(
            select(WorkspaceMember)
            .options(selectinload(WorkspaceMember.user))
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role.in_(("owner", "admin")),
            )
        )
    ).all()
    emails: list[str] = []
    for member in members:
        user = member.user
        if user is None or getattr(user, "is_disabled", False):
            continue
        if user.email:
            emails.append(user.email)
    return emails


async def workspace_name(session: AsyncSession, workspace_id: UUID) -> str:
    row = await session.get(Workspace, workspace_id)
    return row.name if row is not None else "workspace"
