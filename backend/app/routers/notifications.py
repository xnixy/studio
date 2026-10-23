"""In-app notification inbox and preferences."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.dependencies import get_current_user
from app.models import Notification, NotificationPreference, User, WorkspaceMember
from app.schemas import (
    NotificationDto,
    NotificationPreferenceDto,
    NotificationPreferenceUpsertRequest,
    NotificationUnreadCountDto,
)
from app.workspace_access import require_permission

router = APIRouter(tags=["notifications"])


async def _require_member(session: AsyncSession, workspace_id: UUID, user: User) -> WorkspaceMember:
    return await require_permission(session, workspace_id, user, "projects.read")


def _map_notification(row: Notification) -> NotificationDto:
    return NotificationDto(
        id=row.id,
        workspace_id=row.workspace_id,
        type=row.type,
        title=row.title,
        body=row.body,
        href=row.href,
        entity_kind=row.entity_kind,
        entity_id=row.entity_id,
        payload=dict(row.payload or {}),
        read_at=row.read_at,
        created_at=row.created_at,
    )


def _map_pref(row: NotificationPreference) -> NotificationPreferenceDto:
    return NotificationPreferenceDto(
        id=row.id,
        workspace_id=row.workspace_id,
        event_type=row.event_type,
        in_app=row.in_app,
        email=row.email,
        toast=row.toast,
        updated_at=row.updated_at,
    )


@router.get("/notifications", response_model=list[NotificationDto])
async def list_notifications(
    workspace_id: UUID,
    unread_only: bool = False,
    limit: int = Query(default=30, ge=1, le=100),
    before: datetime | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationDto]:
    await _require_member(session, workspace_id, user)
    query = (
        select(Notification)
        .where(Notification.workspace_id == workspace_id, Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    if before is not None:
        query = query.where(Notification.created_at < before)
    rows = (await session.scalars(query)).all()
    return [_map_notification(r) for r in rows]


@router.get("/notifications/unread-count", response_model=NotificationUnreadCountDto)
async def unread_count(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationUnreadCountDto:
    await _require_member(session, workspace_id, user)
    total = await session.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
    )
    return NotificationUnreadCountDto(count=int(total or 0))


@router.post("/notifications/{notification_id}/read", response_model=NotificationDto)
async def mark_read(
    notification_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationDto:
    row = await session.get(Notification, notification_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await _require_member(session, row.workspace_id, user)
    if row.read_at is None:
        row.read_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(row)
    return _map_notification(row)


@router.post("/notifications/read-all", response_model=NotificationUnreadCountDto)
async def mark_all_read(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationUnreadCountDto:
    await _require_member(session, workspace_id, user)
    now = datetime.now(timezone.utc)
    await session.execute(
        update(Notification)
        .where(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
        )
        .values(read_at=now)
    )
    await session.commit()
    return NotificationUnreadCountDto(count=0)


@router.delete("/notifications", response_model=NotificationUnreadCountDto)
async def clear_notifications(
    workspace_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationUnreadCountDto:
    """Remove all inbox rows for this user in the workspace."""
    await _require_member(session, workspace_id, user)
    result = await session.execute(
        delete(Notification).where(
            Notification.workspace_id == workspace_id,
            Notification.user_id == user.id,
        )
    )
    await session.commit()
    # count field = remaining unread (always 0 after clear)
    _ = result.rowcount
    return NotificationUnreadCountDto(count=0)


@router.get("/notification-preferences", response_model=list[NotificationPreferenceDto])
async def list_preferences(
    workspace_id: UUID | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[NotificationPreferenceDto]:
    query = select(NotificationPreference).where(NotificationPreference.user_id == user.id)
    if workspace_id is not None:
        await _require_member(session, workspace_id, user)
        query = query.where(
            (NotificationPreference.workspace_id == workspace_id)
            | (NotificationPreference.workspace_id.is_(None))
        )
    rows = (await session.scalars(query.order_by(NotificationPreference.updated_at.desc()))).all()
    return [_map_pref(r) for r in rows]


@router.put("/notification-preferences", response_model=NotificationPreferenceDto)
async def upsert_preference(
    payload: NotificationPreferenceUpsertRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> NotificationPreferenceDto:
    if payload.workspace_id is not None:
        await _require_member(session, payload.workspace_id, user)
    event_type = (payload.event_type or "*").strip()[:80] or "*"

    existing_q = select(NotificationPreference).where(
        NotificationPreference.user_id == user.id,
        NotificationPreference.event_type == event_type,
    )
    if payload.workspace_id is None:
        existing_q = existing_q.where(NotificationPreference.workspace_id.is_(None))
    else:
        existing_q = existing_q.where(NotificationPreference.workspace_id == payload.workspace_id)
    row = await session.scalar(existing_q)
    if row is None:
        row = NotificationPreference(
            user_id=user.id,
            workspace_id=payload.workspace_id,
            event_type=event_type,
            in_app=payload.in_app,
            email=payload.email,
            toast=payload.toast,
        )
        session.add(row)
    else:
        row.in_app = payload.in_app
        row.email = payload.email
        row.toast = payload.toast
        row.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(row)
    return _map_pref(row)
