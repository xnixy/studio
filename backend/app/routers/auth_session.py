"""Auth session helpers (cookies, tokens)."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Request, Response
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import RefreshToken, User
from app.rate_limit_deps import enforce_rate_limit
from app.schemas import AuthResponse
from app.security import create_access_token, create_refresh_token, hash_refresh_token, map_user


def is_mobile_client(request: Request) -> bool:
    """Native apps send X-Studio-Client: mobile to receive refresh tokens in JSON."""
    return (request.headers.get("x-studio-client") or "").strip().lower() == "mobile"


def auth_response(
    *,
    access_token: str,
    user: User,
    refresh_token: str,
    request: Request,
) -> AuthResponse:
    return AuthResponse(
        access_token=access_token,
        user=map_user(user),
        refresh_token=refresh_token if is_mobile_client(request) else None,
    )


def _refresh_cookie_samesite(settings: Settings) -> str:
    """
    Production SPA is on example.com while the API is on api.example.com.
    Cross-site credentialed fetch needs SameSite=None; Secure.
    Prefer a same-origin /api proxy when possible (then Lax is fine via env).
    """
    mode = (settings.refresh_cookie_samesite or "lax").strip().lower()
    if mode not in {"lax", "strict", "none"}:
        mode = "lax"
    # Browsers require Secure when SameSite=None.
    if mode == "none" and not settings.is_production:
        # Local http://localhost still works with Lax + host-only cookies.
        return "lax"
    return mode


def set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    max_age = settings.refresh_token_days * 24 * 60 * 60
    samesite = _refresh_cookie_samesite(settings)
    secure = settings.is_production or samesite == "none"
    response.set_cookie(
        settings.refresh_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/api/auth",
    )


def clear_refresh_cookie(response: Response, settings: Settings) -> None:
    samesite = _refresh_cookie_samesite(settings)
    secure = settings.is_production or samesite == "none"
    response.delete_cookie(
        settings.refresh_cookie_name,
        httponly=True,
        secure=secure,
        samesite=samesite,
        path="/api/auth",
    )


async def rate_limit(request: Request, key: str, limit: int, window_seconds: int, message: str) -> None:
    # Auth routes: fail closed if Redis is down in production (no multi-instance bypass).
    await enforce_rate_limit(request, key, limit, window_seconds, message, require_redis=True)


async def purge_dead_refresh_tokens(session: AsyncSession, *, older_than_days: int = 30) -> int:
    """Delete expired or long-revoked refresh tokens.

    Rows are never cleaned up otherwise, so the table grows for the life of the
    deployment. Keep recently revoked rows so replay detection can still see them.
    """
    from datetime import timedelta

    from sqlalchemy import delete, or_

    from app.models import RefreshToken

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    result = await session.execute(
        delete(RefreshToken).where(
            or_(RefreshToken.expires_at < cutoff, RefreshToken.revoked_at < cutoff)
        )
    )
    deleted = int(result.rowcount or 0)
    if deleted:
        await session.commit()
    return deleted


def is_rotation_race(stored: RefreshToken, now: datetime, grace_seconds: int) -> bool:
    """True when a revoked token was rotated moments ago by a sibling client.

    Two tabs, or a tab and the phone, can refresh together. The loser presents a
    token the winner just rotated. That is a race to retry, not a leak.
    """
    if stored.revoked_at is None:
        return False
    return (now - stored.revoked_at).total_seconds() <= grace_seconds


async def revoke_refresh_family(session: AsyncSession, stored: RefreshToken, now: datetime) -> None:
    """Revoke the chain a replayed token belongs to, and nothing else.

    Scoped to ``family_id`` on purpose. Revoking every session for the user made
    one device holding a stale token sign the account out everywhere, and a
    stale token is far more often a dropped response than a theft. Rows issued
    before the family column have no chain, so they revoke alone (already done
    by the caller's lookup).
    """
    if stored.family_id is None:
        return
    await session.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == stored.family_id,
            RefreshToken.revoked_at.is_(None),
        )
        .values(revoked_at=now)
    )


async def issue_session(
    session: AsyncSession,
    user: User,
    settings: Settings,
    *,
    family_id: uuid.UUID | None = None,
) -> tuple[str, str]:
    """Mint an access + refresh pair.

    Pass the rotating token's ``family_id`` to keep a chain together; omit it on
    a fresh sign-in to start a new one.
    """
    access_token = create_access_token(user, settings)
    refresh_token = create_refresh_token()
    session.add(
        RefreshToken(
            token_hash=hash_refresh_token(refresh_token),
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_days),
        )
    )
    await session.flush()
    return access_token, refresh_token
