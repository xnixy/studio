"""Built-in / cloned voice listing DTOs."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

PlayVoiceSource = Literal["builtin", "cloned"]
WorkspaceVoiceStatus = Literal["ready", "failed", "deleted"]
VoiceGender = Literal["female", "male", "neutral"]


class PlayVoiceOptionDto(BaseModel):
    """Selectable voice for lip-sync / TTS (built-in or workspace clone)."""

    id: str
    name: str
    description: str = ""
    provider: str = "elevenlabs"
    source: PlayVoiceSource = "builtin"
    available: bool = True
    provider_voice_id: str | None = None
    workspace_voice_id: UUID | None = None
    is_default: bool = False
    gender: str | None = None
    accent: str | None = None
    language: str | None = None


BuiltinVoiceDto = PlayVoiceOptionDto


class CustomVoicesAccessDto(BaseModel):
    """Clone slot access for a workspace. Default cap is 1; admin can raise it."""

    can_clone: bool = False
    clone_cap: int = 1
    clone_count: int = 0


class PlayVoicesResponse(BaseModel):
    voices: list[PlayVoiceOptionDto]
    custom_voices_access: CustomVoicesAccessDto


class WorkspaceVoiceDto(BaseModel):
    id: UUID
    workspace_id: UUID
    label: str
    provider: str = "elevenlabs"
    provider_voice_id: str
    source: Literal["cloned"] = "cloned"
    consent_name: str
    status: WorkspaceVoiceStatus
    gender: str | None = None
    language: str | None = None
    is_default: bool = False
    created_by_id: UUID | None = None
    created_at: datetime
    updated_at: datetime


class VoicePreviewRequest(BaseModel):
    """Short TTS sample for a built-in or workspace clone voice id."""

    workspace_id: UUID
    voice: str = Field(min_length=2, max_length=64)
    text: str | None = Field(default=None, max_length=200)
