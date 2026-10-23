from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import AppEmail, InvitableWorkspaceRole, WorkspaceRole, WorkspaceType

class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    type: WorkspaceType = "personal"


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    type: WorkspaceType


class WorkspaceMemberDto(BaseModel):
    id: UUID
    user_id: UUID | None = None
    email: AppEmail
    role: WorkspaceRole
    status: Literal["active", "pending"] = "active"
    invite_url: str | None = None
    email_sent: bool | None = None
    email_message: str | None = None
    created_at: datetime


class WorkspaceDto(BaseModel):
    id: UUID
    name: str
    type: WorkspaceType
    role: WorkspaceRole
    member_count: int
    billing_workspace_id: UUID
    permissions: list[str] = Field(default_factory=list)
    created_at: datetime


class MemberInviteRequest(BaseModel):
    email: AppEmail
    role: InvitableWorkspaceRole = "editor"


class MemberRoleUpdateRequest(BaseModel):
    role: WorkspaceRole


class InvitationAcceptRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)

__all__ = [
    "WorkspaceCreateRequest",
    "WorkspaceUpdateRequest",
    "WorkspaceMemberDto",
    "WorkspaceDto",
    "MemberInviteRequest",
    "MemberRoleUpdateRequest",
    "InvitationAcceptRequest",
]
