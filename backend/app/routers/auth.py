"""Auth routes: register/login/session."""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth_tokens import PURPOSE_EMAIL_VERIFY, issue_auth_token
from app.config import Settings, get_settings
from app.database import get_session
from app.dependencies import ensure_unique_email, get_admin_user, get_client_ip, get_current_user
from app.email_notify import safe_send_email
from app import email_templates as templates
from app.models import ContactMessage, MaintenanceSetting, RefreshToken, User
from app.rate_limit_deps import enforce_rate_limit
from app.schemas import (
    AdminContactDto,
    AdminUserDto,
    AuthResponse,
    DeleteAccountRequest,
    LoginRequest,
    MaintenanceStatus,
    MaintenanceUpdateRequest,
    MessageResponse,
    MobileLogoutRequest,
    MobileRefreshRequest,
    ProfileUpdateRequest,
    RegisterRequest,
    RoleUpdateRequest,
)
from app.security import create_access_token, hash_password, hash_refresh_token, map_user, verify_password
from app.turnstile import verify_turnstile_token
from app.routers.auth_session import (
    auth_response,
    clear_refresh_cookie,
    is_mobile_client,
    is_rotation_race,
    issue_session,
    rate_limit,
    revoke_refresh_family,
    set_refresh_cookie,
)
from app.routers import auth_password

router = APIRouter(prefix="/auth", tags=["auth"])

# A refresh that lost a race against a sibling tab retries with the new cookie.
# Past this, a revoked token showing up means it leaked.
REFRESH_ROTATION_GRACE_SECONDS = 30

# Tells the client the 401 is a lost rotation race, so retrying with whatever is
# in the jar now will work. Any other 401 means the session is really gone.
REFRESH_RACE_CODE = "refresh_race"

router.include_router(auth_password.router)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    client_ip = get_client_ip(request)
    await rate_limit(
        request,
        f"register:{client_ip}",
        10,
        15 * 60,
        "Too many registration attempts. Please try again later.",
    )
    await verify_turnstile_token(
        payload.turnstile_token,
        settings=settings,
        remote_ip=client_ip,
    )

    email = payload.email.lower()
    await ensure_unique_email(session, email)

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="user",
        permissions={},
    )
    session.add(user)
    await session.flush()

    access_token, refresh_token = await issue_session(session, user, settings)
    verify_raw = await issue_auth_token(
        session, user_id=user.id, purpose=PURPOSE_EMAIL_VERIFY, ttl=timedelta(hours=48)
    )
    await session.commit()
    set_refresh_cookie(response, refresh_token, settings)

    from app.app_links import build_verify_email_app_url, build_verify_email_url

    # Confirm first. Welcome waits until they actually verify.
    verify_url = build_verify_email_url(settings.app_base_url, token=verify_raw)
    app_url = build_verify_email_app_url(token=verify_raw)
    v_subject, v_body = templates.verify_email(verify_url, app_url=app_url)
    await safe_send_email(v_subject, v_body, user.email, settings)

    return auth_response(access_token=access_token, user=user, refresh_token=refresh_token, request=request)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AuthResponse:
    client_ip = get_client_ip(request)
    await rate_limit(request, f"login:{client_ip}", 20, 15 * 60, "Too many login attempts. Please try again later.")
    await rate_limit(
        request,
        f"login-email:{payload.email.lower()}",
        10,
        15 * 60,
        "Too many login attempts for this account. Please try again later.",
    )

    user = await session.scalar(select(User).where(User.email == payload.email.lower()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if getattr(user, "is_disabled", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    if getattr(user, "email_verified_at", None) is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "message": (
                    "Verify your email before signing in. "
                    "Open the confirmation link we sent, or resend it from the verify page."
                ),
                "code": "email_not_verified",
            },
        )

    user.last_login_at = datetime.now(timezone.utc)
    access_token, refresh_token = await issue_session(session, user, settings)
    await session.commit()
    set_refresh_cookie(response, refresh_token, settings)
    return auth_response(access_token=access_token, user=user, refresh_token=refresh_token, request=request)


@router.post(
    "/refresh",
    response_model=AuthResponse,
    responses={204: {"description": "No session cookie or mobile refresh token present (anonymous visitor)"}},
)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    body: MobileRefreshRequest | None = Body(default=None),
) -> AuthResponse | Response:
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_token and body is not None and body.refresh_token:
        raw_token = body.refresh_token.strip() or None
    # Anonymous visits (no cookie / body) are normal on marketing pages — use 204 so browsers
    # and Lighthouse do not log a 401 network error for every cold load.
    if not raw_token:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    # Bucket per token chain, not per IP. Phones share carrier NAT addresses, so
    # an IP bucket let one busy client spend everyone else's budget and sign the
    # whole exit node out. A refresh token is a 32 byte secret, so there is no
    # brute force to rate limit here; the cap only stops one client looping.
    #
    # Deliberately not require_redis: a Redis blip used to 503 every refresh, and
    # since clients drop the session on a failed refresh, that signed out every
    # user at once. Guessing a token remains infeasible without the limiter.
    await enforce_rate_limit(
        request,
        f"refresh:token:{hash_refresh_token(raw_token)}",
        60,
        15 * 60,
        "Too many session refresh attempts. Please try again later.",
    )

    # Lock the row so concurrent refresh cannot mint two sessions from one token.
    # Revoked rows are fetched too: a just-rotated token means a second tab lost
    # a benign race, while an old one means the token leaked and was replayed.
    stored = await session.scalar(
        select(RefreshToken)
        .options(selectinload(RefreshToken.user))
        .where(RefreshToken.token_hash == hash_refresh_token(raw_token))
        .with_for_update()
    )
    now = datetime.now(timezone.utc)

    if stored is not None and stored.revoked_at is not None:
        if is_rotation_race(stored, now, REFRESH_ROTATION_GRACE_SECONDS):
            # The winner already set a fresh cookie; clearing it here is what
            # used to sign both clients out. Let the loser retry with what is in
            # the jar now. The code tells the client this is a retryable race,
            # not a dead session.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"code": REFRESH_RACE_CODE, "message": "Unable to refresh session"},
            )
        # Replay of a long-rotated token: revoke this sign-in's chain only.
        await revoke_refresh_family(session, stored, now)
        await session.commit()
        clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to refresh session")

    if stored is None:
        # Unknown token. Do not clear the cookie: on a shared jar this may be a
        # stale copy racing a refresh that already succeeded.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to refresh session")
    if stored.expires_at <= now:
        clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unable to refresh session")
    if getattr(stored.user, "is_disabled", False):
        stored.revoked_at = datetime.now(timezone.utc)
        await session.commit()
        clear_refresh_cookie(response, settings)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    stored.revoked_at = datetime.now(timezone.utc)
    # Stay in the same chain so a later replay can be scoped to this sign-in.
    access_token, refresh_token = await issue_session(
        session, stored.user, settings, family_id=stored.family_id
    )
    await session.commit()
    set_refresh_cookie(response, refresh_token, settings)
    return auth_response(
        access_token=access_token,
        user=stored.user,
        refresh_token=refresh_token,
        request=request,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
    body: MobileLogoutRequest | None = Body(default=None),
) -> MessageResponse:
    raw_token = request.cookies.get(settings.refresh_cookie_name)
    if not raw_token and body is not None and body.refresh_token:
        raw_token = body.refresh_token.strip() or None
    if raw_token:
        stored = await session.scalar(
            select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token), RefreshToken.revoked_at.is_(None))
        )
        if stored is not None:
            stored.revoked_at = datetime.now(timezone.utc)
            await session.commit()

    clear_refresh_cookie(response, settings)
    return MessageResponse(message="Logged out")


@router.get("/me")
async def me(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {"user": map_user(user)}


@router.patch("/profile")
async def update_profile(
    payload: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    user.full_name = payload.full_name.strip() if payload.full_name and payload.full_name.strip() else None
    await session.commit()
    await session.refresh(user)
    return {"user": map_user(user)}


@router.post("/delete-account", response_model=MessageResponse)
async def delete_account(
    payload: DeleteAccountRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    """Anonymize and disable the signed-in account (App Store account-deletion path).

    Personal data is cleared; the user row is kept for FK integrity and billing audit.
    Login is blocked via is_disabled. All refresh tokens and push tokens are removed.
    """
    await rate_limit(
        request,
        f"delete-account:{user.id}",
        5,
        15 * 60,
        "Too many account deletion attempts. Please try again later.",
    )
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")
    if user.role == "admin":
        # Prevent lockout of the last platform admin via self-service.
        other_admin = await session.scalar(
            select(User.id).where(
                User.role == "admin",
                User.is_disabled.is_(False),
                User.id != user.id,
            )
        )
        if other_admin is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only active admin account",
            )

    now = datetime.now(timezone.utc)
    # Revoke every refresh token for this user.
    tokens = list(
        (await session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)))).all()
    )
    for tok in tokens:
        tok.revoked_at = now

    # Drop push tokens so the device is not messaged after deletion.
    from app.models.devices import DevicePushToken

    devices = list((await session.scalars(select(DevicePushToken).where(DevicePushToken.user_id == user.id))).all())
    for device in devices:
        await session.delete(device)

    user.is_disabled = True
    user.full_name = None
    user.email = f"deleted-{user.id.hex[:12]}@deleted.studio.invalid"
    user.password_hash = hash_password(secrets.token_urlsafe(48))
    user.email_verified_at = None
    user.permissions = {}
    await session.commit()

    clear_refresh_cookie(response, settings)
    return MessageResponse(message="Your account has been deleted")


@router.get("/admin/users", response_model=list[AdminUserDto])
async def list_users(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[AdminUserDto]:
    users = (await session.scalars(select(User).order_by(User.created_at))).all()
    return [
        AdminUserDto(
            id=user.id,
            email=user.email,
            created_at=user.created_at,
            role=user.role,  # type: ignore[arg-type]
            permissions=user.permissions or {},
            full_name=user.full_name,
            is_disabled=bool(getattr(user, "is_disabled", False)),
            last_login_at=getattr(user, "last_login_at", None),
        )
        for user in users
    ]


@router.patch("/admin/users/{user_id}/role", response_model=MessageResponse)
async def update_user_role(
    user_id: UUID,
    payload: RoleUpdateRequest,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    if admin.id == user_id and payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot remove their own admin role")

    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.role = payload.role
    await session.commit()
    return MessageResponse(message="Role updated")


@router.get("/admin/contacts", response_model=list[AdminContactDto])
async def list_contacts(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[AdminContactDto]:
    contacts = (await session.scalars(select(ContactMessage).order_by(ContactMessage.created_at.desc()))).all()
    return [
        AdminContactDto(
            id=contact.id,
            name=contact.name,
            email=contact.email,
            topic=contact.topic,  # type: ignore[arg-type]
            message=contact.message,
            created_at=contact.created_at,
            resolved_at=getattr(contact, "resolved_at", None),
        )
        for contact in contacts
    ]


@router.get("/admin/maintenance", response_model=MaintenanceStatus)
async def get_admin_maintenance(
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MaintenanceStatus:
    setting = await session.get(MaintenanceSetting, 1)
    return MaintenanceStatus(enabled=setting.enabled if setting else False, message=setting.message if setting else None)


@router.post("/admin/maintenance", response_model=MaintenanceStatus)
async def set_admin_maintenance(
    payload: MaintenanceUpdateRequest,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MaintenanceStatus:
    setting = await session.get(MaintenanceSetting, 1)
    if setting is None:
        setting = MaintenanceSetting(id=1)
        session.add(setting)

    setting.enabled = payload.enabled
    setting.message = payload.message.strip() if payload.message and payload.message.strip() else None
    await session.commit()
    await session.refresh(setting)
    return MaintenanceStatus(enabled=setting.enabled, message=setting.message)
