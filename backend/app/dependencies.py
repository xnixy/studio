from __future__ import annotations

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import get_session
from app.models import User
from app.security import decode_access_token, parse_user_id

# Stable client code for paywall-style handling on web/mobile.
CODE_EMAIL_NOT_VERIFIED = "email_not_verified"

# Unverified users may only hit these after login/register (session still issued for resend UX).
_UNVERIFIED_ALLOWED_PATHS = frozenset(
    {
        "/api/auth/me",
        "/api/auth/logout",
        "/api/auth/resend-verification",
        "/api/auth/delete-account",
    }
)


def unverified_request_allowed(path: str) -> bool:
    """True when an unverified session may hit this API path."""
    normalized = (path or "").rstrip("/") or "/"
    return normalized in _UNVERIFIED_ALLOWED_PATHS


def _raise_email_not_verified() -> None:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "message": "Verify your email before continuing. Check your inbox for a confirmation link.",
            "code": CODE_EMAIL_NOT_VERIFIED,
        },
    )


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token, settings)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required") from None

    user_id = parse_user_id(payload.get("sub"))
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    if getattr(user, "is_disabled", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    if getattr(user, "email_verified_at", None) is None:
        if not unverified_request_allowed(request.url.path):
            _raise_email_not_verified()

    return user


async def get_optional_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> User | None:
    """Bearer user when present; None when anonymous (does not 401)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token, settings)
    except jwt.PyJWTError:
        return None
    user_id = parse_user_id(payload.get("sub"))
    if user_id is None:
        return None
    user = await session.get(User, user_id)
    if user is None or getattr(user, "is_disabled", False):
        return None
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def get_client_ip(request: Request) -> str:
    """Best-effort client IP for rate limiting.

    Trust X-Forwarded-For / CF-Connecting-IP only when TRUST_PROXY_HEADERS is enabled
    (set behind Cloudflare/nginx). Otherwise client-supplied headers would bypass limits.
    """
    settings = get_settings()
    if getattr(settings, "trust_proxy_headers", False):
        cf = request.headers.get("cf-connecting-ip")
        if cf and cf.strip():
            return cf.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",", 1)[0].strip()
    return request.client.host if request.client else "unknown"


async def ensure_unique_email(session: AsyncSession, email: str) -> None:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")
