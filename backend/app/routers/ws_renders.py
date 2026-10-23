"""WebSocket: workspace live channel (+ legacy render-queue endpoint).

Auth: short-lived WS ticket from POST /api/ws/ticket (preferred), or access token
via first text message `{"type":"auth","token":"..."}`. Query-string JWT is still
accepted for one release for compatibility but is not recommended (proxy logs).
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.database import SessionLocal, get_session
from app.dependencies import get_current_user
from app.events.hub import event_hub
from app.models import User, VideoRender, WorkspaceMember
from app.security import decode_access_token, parse_user_id

router = APIRouter(tags=["ws"])

WS_TICKET_TTL_SECONDS = 120


class WsTicketRequest(BaseModel):
    workspace_id: UUID


class WsTicketResponse(BaseModel):
    ticket: str = Field(description="Short-lived ticket for WebSocket query param `ticket`")
    expires_in: int


def _ticket_secret(settings: Settings) -> bytes:
    return settings.jwt_signing_key.encode("utf-8")


def create_ws_ticket(*, user_id: UUID, workspace_id: UUID, settings: Settings) -> str:
    exp = int(time.time()) + WS_TICKET_TTL_SECONDS
    body = f"{user_id}:{workspace_id}:{exp}"
    sig = hmac.new(_ticket_secret(settings), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}:{sig}"


def verify_ws_ticket(ticket: str, settings: Settings) -> tuple[UUID, UUID] | None:
    parts = ticket.split(":")
    if len(parts) != 4:
        return None
    user_s, workspace_s, exp_s, sig = parts
    try:
        exp = int(exp_s)
        user_id = UUID(user_s)
        workspace_id = UUID(workspace_s)
    except (ValueError, TypeError):
        return None
    if exp < int(time.time()):
        return None
    body = f"{user_id}:{workspace_id}:{exp}"
    expected = hmac.new(_ticket_secret(settings), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return user_id, workspace_id


@router.post("/ws/ticket", response_model=WsTicketResponse)
async def issue_ws_ticket(
    payload: WsTicketRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> WsTicketResponse:
    membership = await session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == payload.workspace_id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return WsTicketResponse(
        ticket=create_ws_ticket(user_id=user.id, workspace_id=payload.workspace_id, settings=settings),
        expires_in=WS_TICKET_TTL_SECONDS,
    )


async def _queue_snapshot(workspace_id: UUID) -> dict:
    async with SessionLocal() as session:
        rows = (
            await session.scalars(
                select(VideoRender)
                .where(
                    VideoRender.workspace_id == workspace_id,
                    VideoRender.status.in_(("queued", "processing", "rendering", "uploading")),
                )
                .order_by(VideoRender.created_at.asc())
                .limit(40)
            )
        ).all()
        queued = sum(1 for r in rows if r.status in {"queued", "processing"})
        running = sum(1 for r in rows if r.status in {"rendering", "uploading"})
        return {
            "type": "render_queue",
            "workspace_id": str(workspace_id),
            "queued": queued,
            "running": running,
            "items": [
                {
                    "id": str(r.id),
                    "status": r.status,
                    "video_project_id": str(r.video_project_id),
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "error_message": r.error_message,
                }
                for r in rows
            ],
        }


async def _authorize_ws(
    websocket: WebSocket,
    *,
    workspace_id: UUID,
    ticket: str | None,
    legacy_token: str | None,
    settings: Settings,
) -> tuple[UUID, str | None] | None:
    """Return (user_id, display_name) if authorized."""
    user_id: UUID | None = None

    if ticket:
        parsed = verify_ws_ticket(ticket, settings)
        if parsed is None:
            return None
        ticket_user, ticket_ws = parsed
        if ticket_ws != workspace_id:
            return None
        user_id = ticket_user
    elif legacy_token:
        try:
            payload = decode_access_token(legacy_token, settings)
            parsed = parse_user_id(payload.get("sub"))
            if parsed is None:
                return None
            user_id = parsed
        except jwt.PyJWTError:
            return None
    else:
        try:
            raw = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            message = json.loads(raw)
            if not isinstance(message, dict) or message.get("type") != "auth":
                return None
            token = str(message.get("token") or "")
            payload = decode_access_token(token, settings)
            parsed = parse_user_id(payload.get("sub"))
            if parsed is None:
                return None
            user_id = parsed
        except (asyncio.TimeoutError, json.JSONDecodeError, jwt.PyJWTError, WebSocketDisconnect):
            return None

    display_name: str | None = None
    async with SessionLocal() as session:
        membership = await session.scalar(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        if membership is None:
            return None
        user = await session.get(User, user_id)
        if user is not None:
            display_name = user.full_name or user.email
    return user_id, display_name


async def _safe_send_json(websocket: WebSocket, payload: dict) -> bool:
    """Send JSON if the socket is still open. Returns False when the client is gone."""
    try:
        await websocket.send_json(payload)
        return True
    except (WebSocketDisconnect, RuntimeError):
        # RuntimeError: "Unexpected ASGI message 'websocket.send' after websocket.close"
        return False


async def _workspace_ws_loop(
    websocket: WebSocket,
    *,
    workspace_id: UUID,
    user_id: UUID,
    display_name: str | None,
    render_only: bool,
) -> None:
    ws_key = str(workspace_id)
    queue = await event_hub.subscribe(ws_key)
    closed = asyncio.Event()

    async def _client_reader() -> None:
        try:
            while not closed.is_set():
                raw = await websocket.receive_text()
                try:
                    message = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(message, dict):
                    continue
                mtype = message.get("type")
                if mtype == "presence.heartbeat":
                    path = str(message.get("path") or "")[:300] or None
                    await event_hub.presence_touch(
                        ws_key, str(user_id), display_name=display_name, path=path
                    )
                elif mtype == "ping":
                    if not await _safe_send_json(websocket, {"type": "pong"}):
                        closed.set()
                        return
        except WebSocketDisconnect:
            closed.set()
        except Exception:
            closed.set()

    reader_task: asyncio.Task[None] | None = None
    try:
        await event_hub.presence_touch(ws_key, str(user_id), display_name=display_name)
        if not await _safe_send_json(
            websocket,
            {
                "type": "hello",
                "workspace_id": ws_key,
                "user_id": str(user_id),
                "render_only": render_only,
            },
        ):
            return
        if not await _safe_send_json(websocket, await _queue_snapshot(workspace_id)):
            return
        if not render_only:
            if not await _safe_send_json(
                websocket,
                {
                    "type": "presence.snapshot",
                    "workspace_id": ws_key,
                    "members": await event_hub.presence_snapshot(ws_key),
                },
            ):
                return
            # Fan-out to *other* clients; ignore send failures on this socket via hub path.
            try:
                await event_hub.publish(
                    {
                        "type": "presence.join",
                        "workspace_id": ws_key,
                        "user_id": str(user_id),
                        "display_name": display_name or "",
                    }
                )
            except Exception:
                pass

        reader_task = asyncio.create_task(_client_reader())
        while not closed.is_set():
            try:
                event = await asyncio.wait_for(queue.get(), timeout=8.0)
            except asyncio.TimeoutError:
                if closed.is_set():
                    break
                await event_hub.presence_touch(ws_key, str(user_id), display_name=display_name)
                if not await _safe_send_json(websocket, await _queue_snapshot(workspace_id)):
                    closed.set()
                    break
                continue

            if closed.is_set() or not isinstance(event, dict):
                continue
            et = str(event.get("type") or "")
            is_render = et in {"render_status", "render_queue"} or et.startswith("render.")
            if render_only and not is_render:
                continue
            if et in {
                "render_status",
                "render_queue",
                "presence.join",
                "presence.leave",
                "presence.snapshot",
            }:
                if not await _safe_send_json(websocket, event):
                    closed.set()
                    break
                if et == "render_status":
                    if not await _safe_send_json(websocket, await _queue_snapshot(workspace_id)):
                        closed.set()
                        break
            else:
                if not await _safe_send_json(websocket, {"type": "event", "event": event}):
                    closed.set()
                    break
    except WebSocketDisconnect:
        closed.set()
    finally:
        closed.set()
        if reader_task is not None:
            reader_task.cancel()
            try:
                await reader_task
            except (asyncio.CancelledError, Exception):
                pass
        await event_hub.unsubscribe(ws_key, queue)
        if not render_only:
            await event_hub.presence_leave(ws_key, str(user_id))
            try:
                await event_hub.publish(
                    {
                        "type": "presence.leave",
                        "workspace_id": ws_key,
                        "user_id": str(user_id),
                    }
                )
            except Exception:
                pass


@router.websocket("/ws/workspace")
async def workspace_ws(
    websocket: WebSocket,
    workspace_id: UUID = Query(...),
    ticket: str | None = Query(default=None),
    token: str | None = Query(default=None),
) -> None:
    await websocket.accept()
    settings = get_settings()
    auth = await _authorize_ws(
        websocket,
        workspace_id=workspace_id,
        ticket=ticket,
        legacy_token=token,
        settings=settings,
    )
    if auth is None:
        await websocket.send_json({"type": "error", "detail": "Invalid or expired credentials"})
        await websocket.close(code=4401)
        return
    user_id, display_name = auth
    await _workspace_ws_loop(
        websocket,
        workspace_id=workspace_id,
        user_id=user_id,
        display_name=display_name,
        render_only=False,
    )


@router.websocket("/ws/renders")
async def render_queue_ws(
    websocket: WebSocket,
    workspace_id: UUID = Query(...),
    ticket: str | None = Query(default=None),
    token: str | None = Query(default=None),
) -> None:
    """Legacy render-queue socket; prefer /ws/workspace."""
    await websocket.accept()
    settings = get_settings()
    auth = await _authorize_ws(
        websocket,
        workspace_id=workspace_id,
        ticket=ticket,
        legacy_token=token,
        settings=settings,
    )
    if auth is None:
        await websocket.send_json({"type": "error", "detail": "Invalid or expired credentials"})
        await websocket.close(code=4401)
        return
    user_id, display_name = auth
    await _workspace_ws_loop(
        websocket,
        workspace_id=workspace_id,
        user_id=user_id,
        display_name=display_name,
        render_only=True,
    )
