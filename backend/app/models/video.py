from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import BigInteger, Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import utcnow


class VideoProject(Base):
    __tablename__ = "video_projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    parent_video_project_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    variant_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    title: Mapped[str] = mapped_column(String(180))
    platform: Mapped[str] = mapped_column(String(32))
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16")
    target_duration_seconds: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    project_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    scenes: Mapped[list[VideoScene]] = relationship(back_populates="project", cascade="all, delete-orphan")
    renders: Mapped[list[VideoRender]] = relationship(back_populates="project", cascade="all, delete-orphan")
    assets: Mapped[list[VideoAsset]] = relationship(back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("platform in ('tiktok', 'instagram_reels', 'youtube_shorts', 'meta_feed', 'meta_story')", name="ck_video_projects_platform"),
        CheckConstraint("aspect_ratio in ('9:16', '1:1', '4:5')", name="ck_video_projects_aspect_ratio"),
        # Play clips are often 4–15s; longer multi-scene projects stay within 3 min.
        CheckConstraint(
            "target_duration_seconds >= 1 AND target_duration_seconds <= 180",
            name="ck_video_projects_target_duration",
        ),
        CheckConstraint("status in ('draft', 'ready', 'rendering', 'complete', 'failed', 'archived')", name="ck_video_projects_status"),
    )


class VideoScene(Base):
    __tablename__ = "video_scenes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    sequence_index: Mapped[int] = mapped_column(Integer)
    scene_type: Mapped[str] = mapped_column(String(32), default="storyboard")
    start_time_ms: Mapped[int] = mapped_column(Integer)
    end_time_ms: Mapped[int] = mapped_column(Integer)
    spoken_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    on_screen_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    transition: Mapped[str] = mapped_column(String(32), default="cut")
    scene_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped[VideoProject] = relationship(back_populates="scenes")
    assets: Mapped[list[VideoAsset]] = relationship(back_populates="scene", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("video_project_id", "sequence_index", name="uq_video_scenes_project_sequence"),
        CheckConstraint("sequence_index >= 0", name="ck_video_scenes_sequence_nonnegative"),
        CheckConstraint("start_time_ms >= 0", name="ck_video_scenes_start_nonnegative"),
        CheckConstraint("end_time_ms > start_time_ms", name="ck_video_scenes_end_after_start"),
        CheckConstraint("scene_type in ('storyboard', 'product', 'text_card', 'end_card')", name="ck_video_scenes_type"),
    )


class VideoRender(Base):
    __tablename__ = "video_renders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    output_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    render_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped[VideoProject] = relationship(back_populates="renders")
    jobs: Mapped[list[RenderJob]] = relationship(back_populates="render", cascade="all, delete-orphan")
    caption_tracks: Mapped[list[CaptionTrack]] = relationship(back_populates="render", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("status in ('queued', 'processing', 'rendering', 'uploading', 'complete', 'failed', 'canceled')", name="ck_video_renders_status"),
    )


class RenderJob(Base):
    __tablename__ = "render_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    video_render_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_renders.id", ondelete="CASCADE"), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_metadata: Mapped[dict[str, object]] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    render: Mapped[VideoRender] = relationship(back_populates="jobs")

    __table_args__ = (
        UniqueConstraint("workspace_id", "idempotency_key", name="uq_render_jobs_workspace_idempotency"),
        CheckConstraint("status in ('queued', 'processing', 'waiting_for_provider', 'rendering', 'uploading', 'complete', 'failed', 'canceled')", name="ck_render_jobs_status"),
        CheckConstraint("attempts >= 0", name="ck_render_jobs_attempts_nonnegative"),
    )


class CaptionTrack(Base):
    __tablename__ = "caption_tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    video_render_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_renders.id", ondelete="CASCADE"), index=True)
    format: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(16), default="en")
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    burned_in: Mapped[bool] = mapped_column(Boolean, default=False)
    track_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    render: Mapped[VideoRender] = relationship(back_populates="caption_tracks")

    __table_args__ = (
        UniqueConstraint("video_render_id", "format", "language", name="uq_caption_tracks_render_format_language"),
        CheckConstraint("format in ('vtt', 'srt', 'ass', 'burn_in')", name="ck_caption_tracks_format"),
    )


class VideoAsset(Base):
    __tablename__ = "video_assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    video_project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("video_projects.id", ondelete="CASCADE"), index=True)
    video_scene_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("video_scenes.id", ondelete="CASCADE"), nullable=True, index=True)
    asset_type: Mapped[str] = mapped_column(String(32))
    source: Mapped[str] = mapped_column(String(32), default="xai")
    status: Mapped[str] = mapped_column(String(32), default="queued")
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    provider_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    storage_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    cost_usd_ticks: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped[VideoProject] = relationship(back_populates="assets")
    scene: Mapped[VideoScene | None] = relationship(back_populates="assets")

    __table_args__ = (
        CheckConstraint("asset_type in ('image', 'video', 'audio', 'stock', 'upload', 'render', 'text_card')", name="ck_video_assets_type"),
        CheckConstraint(
            "source in ('xai', 'sync_labs', 'gemini', 'seedance', 'kling', 'upload', 'stock', 'render', 'system')",
            name="ck_video_assets_source",
        ),
        CheckConstraint("status in ('queued', 'processing', 'ready', 'failed', 'expired')", name="ck_video_assets_status"),
    )


class GenerationCost(Base):
    __tablename__ = "generation_costs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    feature: Mapped[str] = mapped_column(String(80))
    provider: Mapped[str] = mapped_column(String(32))
    provider_model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    provider_request_id: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    cost_usd_ticks: Mapped[int] = mapped_column(BigInteger, default=0)
    cost_metadata: Mapped[dict[str, object]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        CheckConstraint("cost_usd_ticks >= 0", name="ck_generation_costs_ticks_nonnegative"),
    )

__all__ = [
    "VideoProject",
    "VideoScene",
    "VideoRender",
    "RenderJob",
    "CaptionTrack",
    "VideoAsset",
    "GenerationCost",
]
