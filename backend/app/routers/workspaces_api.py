"""Workspace API: single personal space per user.

Multi-workspace create/switch and team invites were removed from the product.
"""
from __future__ import annotations

from app.routers._platform_shared import *  # noqa: F403
from fastapi import APIRouter

router = APIRouter(tags=["workspaces"])

_TEAM_GONE = (
    "Team workspaces and multi-space accounts are no longer supported. "
    "Each account has one personal space."
)


def _gone() -> None:
    raise HTTPException(status_code=status.HTTP_410_GONE, detail=_TEAM_GONE)


@router.get("/workspaces", response_model=list[WorkspaceDto])
async def list_workspaces(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[WorkspaceDto]:
    """Return the caller's personal workspace (created if missing)."""
    personal = await ensure_personal_workspace(session, user)
    membership = await session.scalar(
        select(WorkspaceMember)
        .options(selectinload(WorkspaceMember.workspace).selectinload(Workspace.members))
        .where(
            WorkspaceMember.user_id == user.id,
            WorkspaceMember.workspace_id == personal.id,
        )
    )
    if membership is not None:
        return [map_workspace(membership.workspace, membership)]

    workspace = await session.scalar(
        select(Workspace)
        .options(selectinload(Workspace.members))
        .where(Workspace.id == personal.id)
    )
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    membership = await get_membership(session, personal.id, user)
    return [map_workspace(workspace, membership)]


@router.post("/workspaces")
async def create_workspace(_: User = Depends(get_current_user)) -> None:
    _gone()


@router.patch("/workspaces/{workspace_id}")
async def update_workspace(workspace_id: UUID, _: User = Depends(get_current_user)) -> None:
    _gone()


@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(workspace_id: UUID, _: User = Depends(get_current_user)) -> None:
    _gone()


@router.get("/workspaces/{workspace_id}/members")
async def list_members(workspace_id: UUID, _: User = Depends(get_current_user)) -> None:
    _gone()


@router.post("/workspaces/{workspace_id}/members")
async def invite_member(workspace_id: UUID, _: User = Depends(get_current_user)) -> None:
    _gone()


@router.post("/workspaces/invitations/accept")
async def accept_invitation(_: User = Depends(get_current_user)) -> None:
    _gone()


@router.patch("/workspaces/{workspace_id}/members/{member_id}")
async def update_member_role(
    workspace_id: UUID,
    member_id: UUID,
    _: User = Depends(get_current_user),
) -> None:
    _gone()


@router.delete("/workspaces/{workspace_id}/members/{member_id}")
async def remove_member(
    workspace_id: UUID,
    member_id: UUID,
    _: User = Depends(get_current_user),
) -> None:
    _gone()
