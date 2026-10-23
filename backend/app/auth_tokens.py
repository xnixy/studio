"""One-time auth email tokens (password reset + email verify)."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuthEmailToken, User

PURPOSE_PASSWORD_RESET = "password_reset"
PURPOSE_EMAIL_VERIFY = "email_verify"


def hash_auth_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_raw_token() -> str:
    return secrets.token_urlsafe(32)


async def issue_auth_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    purpose: str,
    ttl: timedelta,
) -> str:
    """Invalidate prior unused tokens for this purpose and issue a new raw token."""
    now = datetime.now(timezone.utc)
    await session.execute(
        update(AuthEmailToken)
        .where(
            AuthEmailToken.user_id == user_id,
            AuthEmailToken.purpose == purpose,
            AuthEmailToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    raw = new_raw_token()
    session.add(
        AuthEmailToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=hash_auth_token(raw),
            expires_at=now + ttl,
        )
    )
    await session.flush()
    return raw


async def consume_auth_token(
    session: AsyncSession,
    *,
    raw_token: str,
    purpose: str,
) -> User | None:
    now = datetime.now(timezone.utc)
    token = await session.scalar(
        select(AuthEmailToken)
        .options(selectinload(AuthEmailToken.user))
        .where(
            AuthEmailToken.token_hash == hash_auth_token(raw_token),
            AuthEmailToken.purpose == purpose,
            AuthEmailToken.used_at.is_(None),
        )
        .with_for_update()
    )
    if token is None or token.expires_at <= now:
        return None
    token.used_at = now
    return token.user
