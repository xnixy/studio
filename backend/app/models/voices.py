"""Workspace cloned voices (ElevenLabs IVC; legacy xAI rows still resolve)."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import utcnow


class WorkspaceVoice(Base):
    """Workspace-scoped cloned voice."""

    __tablename__ = "workspace_voices"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(32), default="elevenlabs")
    provider_voice_id: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(32), default="cloned")
    consent_name: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(16), default="ready", index=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    __table_args__ = (
        CheckConstraint(
            "status in ('ready', 'failed', 'deleted')",
            name="ck_workspace_voices_status",
        ),
        CheckConstraint(
            "source in ('cloned')",
            name="ck_workspace_voices_source",
        ),
        CheckConstraint(
            "provider in ('elevenlabs', 'xai')",
            name="ck_workspace_voices_provider",
        ),
        CheckConstraint(
            "gender is null or gender in ('female', 'male', 'neutral')",
            name="ck_workspace_voices_gender",
        ),
    )


__all__ = ["WorkspaceVoice"]
