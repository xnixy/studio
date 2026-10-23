"""Password + email verification routes (mounted on auth router)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth_tokens import (
    PURPOSE_EMAIL_VERIFY,
    PURPOSE_PASSWORD_RESET,
    consume_auth_token,
    issue_auth_token,
)
from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import get_client_ip, get_current_user, get_optional_user
from app.email_notify import safe_send_email
from app import email_templates as templates
from app.models import RefreshToken, User
from app.rate_limit_deps import enforce_rate_limit
from app.schemas import (
    ForgotPasswordRequest,
    MessageResponse,
    PasswordUpdateRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from app.schemas.common import AppEmail
from app.security import hash_password, verify_password
from app.routers.auth_session import clear_refresh_cookie
from app.workspace_access import ensure_personal_workspace

router = APIRouter()
logger = logging.getLogger(__name__)


class ResendVerificationRequest(BaseModel):
    """Optional body when signed out: resend by email (anti-enumeration response)."""

    email: AppEmail | None = Field(default=None)


async def rate_limit(request: Request, key: str, limit: int, window_seconds: int, message: str) -> None:
    await enforce_rate_limit(request, key, limit, window_seconds, message, require_redis=True)

@router.post("/password", response_model=MessageResponse)
async def update_password(
    payload: PasswordUpdateRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    user.password_hash = hash_password(payload.password)
    # Invalidate all refresh sessions so a stolen cookie cannot outlive a password change.
    tokens = (
        await session.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        )
    ).all()
    now = datetime.now(timezone.utc)
    for stored in tokens:
        stored.revoked_at = now
    await session.commit()
    clear_refresh_cookie(response, settings)
    subject, body = templates.password_changed()
    await safe_send_email(subject, body, user.email, settings)
    return MessageResponse(message="Password updated. Sign in again on all devices.")


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    await rate_limit(
        request,
        f"forgot-password:{get_client_ip(request)}",
        8,
        15 * 60,
        "Too many password reset attempts. Please try again later.",
    )
    await rate_limit(
        request,
        f"forgot-password-email:{payload.email.lower()}",
        5,
        15 * 60,
        "Too many password reset attempts for this email. Please try again later.",
    )
    # Always return the same message to avoid account enumeration.
    generic = MessageResponse(message="If an account exists for that email, we sent password reset instructions.")
    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or getattr(user, "is_disabled", False):
        return generic
    raw = await issue_auth_token(
        session, user_id=user.id, purpose=PURPOSE_PASSWORD_RESET, ttl=timedelta(hours=1)
    )
    await session.commit()
    reset_url = f"{settings.app_base_url.rstrip('/')}/reset-password?token={raw}"
    subject, body = templates.password_reset(reset_url)
    await safe_send_email(subject, body, user.email, settings)
    return generic


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    await rate_limit(
        request,
        f"reset-password:{get_client_ip(request)}",
        10,
        15 * 60,
        "Too many password reset attempts. Please try again later.",
    )
    user = await consume_auth_token(session, raw_token=payload.token, purpose=PURPOSE_PASSWORD_RESET)
    if user is None or getattr(user, "is_disabled", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset link")
    user.password_hash = hash_password(payload.password)
    tokens = (
        await session.scalars(
            select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
        )
    ).all()
    now = datetime.now(timezone.utc)
    for stored in tokens:
        stored.revoked_at = now
    await session.commit()
    subject, body = templates.password_changed()
    await safe_send_email(subject, body, user.email, settings)
    return MessageResponse(message="Password reset. You can sign in with your new password.")


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    payload: VerifyEmailRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    await rate_limit(
        request,
        f"verify-email:{get_client_ip(request)}",
        20,
        15 * 60,
        "Too many verification attempts. Please try again later.",
    )
    user = await consume_auth_token(session, raw_token=payload.token, purpose=PURPOSE_EMAIL_VERIFY)
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired verification link")
    just_verified = user.email_verified_at is None
    if just_verified:
        user.email_verified_at = datetime.now(timezone.utc)
    await session.commit()
    if just_verified:
        try:
            await ensure_personal_workspace(session, user)
        except Exception:
            # Verify already committed. List workspaces will create the space later.
            logger.exception("Could not create personal workspace after verify for user %s", user.id)
        subject, body = templates.welcome(settings.app_base_url)
        await safe_send_email(subject, body, user.email, settings)
    return MessageResponse(message="Email verified.")


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    request: Request,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    user: User | None = Depends(get_optional_user),
    body: ResendVerificationRequest | None = Body(default=None),
) -> MessageResponse:
    """Resend verify link. Prefer signed-in user; else email body (login recovery)."""
    from app.app_links import build_verify_email_app_url, build_verify_email_url

    target: User | None = user
    if target is None and body is not None and body.email:
        await rate_limit(
            request,
            f"resend-verify-ip:{get_client_ip(request)}",
            8,
            15 * 60,
            "Too many verification emails. Please try again later.",
        )
        await rate_limit(
            request,
            f"resend-verify-email:{body.email.lower()}",
            5,
            15 * 60,
            "Too many verification emails for this address. Please try again later.",
        )
        target = await session.scalar(select(User).where(User.email == body.email.lower()))
        # Anti-enumeration: same message whether missing, verified, or sent.
        generic = MessageResponse(
            message="If that account needs verification, we sent a new confirmation link."
        )
        if target is None or getattr(target, "is_disabled", False):
            return generic
        if target.email_verified_at is not None:
            return generic
        raw = await issue_auth_token(
            session, user_id=target.id, purpose=PURPOSE_EMAIL_VERIFY, ttl=timedelta(hours=48)
        )
        await session.commit()
        verify_url = build_verify_email_url(settings.app_base_url, token=raw)
        app_url = build_verify_email_app_url(token=raw)
        subject, text = templates.verify_email(verify_url, app_url=app_url)
        await safe_send_email(subject, text, target.email, settings)
        return generic

    if target is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    await rate_limit(
        request,
        f"resend-verify:{target.id}",
        5,
        15 * 60,
        "Too many verification emails. Please try again later.",
    )
    if target.email_verified_at is not None:
        return MessageResponse(message="Email is already verified.")
    raw = await issue_auth_token(
        session, user_id=target.id, purpose=PURPOSE_EMAIL_VERIFY, ttl=timedelta(hours=48)
    )
    await session.commit()
    verify_url = build_verify_email_url(settings.app_base_url, token=raw)
    app_url = build_verify_email_app_url(token=raw)
    subject, text = templates.verify_email(verify_url, app_url=app_url)
    sent, err = await safe_send_email(subject, text, target.email, settings)
    if not sent:
        return MessageResponse(message=f"Could not send verification email ({err}).")
    return MessageResponse(message="Verification email sent.")


