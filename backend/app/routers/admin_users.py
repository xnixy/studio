"""admin_users platform admin routes."""
from __future__ import annotations

from app.routers._admin_shared import *  # noqa: F403
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/users", response_model=list[AdminUserDto])
async def list_users(
    q: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> list[AdminUserDto]:
    stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
    if q and q.strip():
        term = f"%{q.strip().lower()}%"
        stmt = stmt.where(or_(func.lower(User.email).like(term), func.lower(func.coalesce(User.full_name, "")).like(term)))
    users = list((await session.scalars(stmt)).all())
    counts: dict[UUID, int] = {}
    if users:
        rows = (
            await session.execute(
                select(WorkspaceMember.user_id, func.count())
                .where(WorkspaceMember.user_id.in_([u.id for u in users]))
                .group_by(WorkspaceMember.user_id)
            )
        ).all()
        counts = {uid: int(c) for uid, c in rows}
    return [map_admin_user(user, counts.get(user.id, 0)) for user in users]


@router.patch("/users/{user_id}", response_model=AdminUserDto)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    admin: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> AdminUserDto:
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.role is not None:
        if admin.id == user_id and payload.role != "admin":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot remove their own admin role")
        user.role = payload.role
    became_disabled = False
    if payload.is_disabled is not None:
        if admin.id == user_id and payload.is_disabled:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot disable their own account")
        became_disabled = bool(payload.is_disabled) and not bool(user.is_disabled)
        user.is_disabled = payload.is_disabled
        if payload.is_disabled:
            tokens = (await session.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)))).all()
            now = _utcnow()
            for token in tokens:
                token.revoked_at = now
    if payload.permissions is not None:
        user.permissions = {str(key): bool(value) for key, value in payload.permissions.items()}
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip() or None
    await session.commit()
    await session.refresh(user)
    if became_disabled:
        from app import email_templates as templates
        from app.config import get_settings
        from app.email_notify import safe_send_email

        subject, body = templates.account_disabled()
        await safe_send_email(subject, body, user.email, get_settings())
    count = int(await session.scalar(select(func.count()).select_from(WorkspaceMember).where(WorkspaceMember.user_id == user.id)) or 0)
    return map_admin_user(user, count)


@router.post("/users/{user_id}/revoke-sessions", response_model=MessageResponse)
async def revoke_sessions(
    user_id: UUID,
    _: User = Depends(get_admin_user),
    session: AsyncSession = Depends(get_session),
) -> MessageResponse:
    tokens = (await session.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)))).all()
    now = _utcnow()
    for token in tokens:
        token.revoked_at = now
    await session.commit()
    return MessageResponse(message=f"Revoked {len(tokens)} session(s)")


