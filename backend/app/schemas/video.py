"""Video DTOs still used by Play poll + optional project mapping."""
from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

VideoPlatform = Literal["tiktok", "instagram_reels", "youtube_shorts", "meta_feed", "meta_story"]
VideoAspectRatio = Literal["9:16", "1:1", "4:5"]
VideoProjectStatus = Literal["draft", "ready", "rendering", "complete", "failed", "archived"]
VideoSceneType = Literal["storyboard", "product", "text_card", "end_card"]
VideoTransition = Literal["cut", "fade", "slide"]
RenderStatus = Literal["queued", "processing", "rendering", "uploading", "complete", "failed", "canceled"]
RenderJobStatus = Literal["queued", "processing", "waiting_for_provider", "rendering", "uploading", "complete", "failed", "canceled"]
VideoAssetType = Literal["image", "video", "audio", "stock", "upload", "render", "text_card"]
VideoAssetSource = Literal["xai", "sync_labs", "gemini", "seedance", "kling", "upload", "stock", "render", "system"]
VideoAssetStatus = Literal["queued", "processing", "ready", "failed", "expired"]
XaiImageResolution = Literal["1k", "2k"]
XaiVideoResolution = Literal["480p", "720p", "1080p"]


class CaptionTrackDto(BaseModel):
    id: UUID
    workspace_id: UUID
    video_render_id: UUID
    format: Literal["vtt", "srt", "ass", "burn_in"]
    language: str
    url: str | None = None
    burned_in: bool
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class VideoProviderStatusDto(BaseModel):
    provider: str
    configured: bool
    model: str | None = None
    status: Literal["ready", "needs_configuration", "unavailable"]
    message: str


class VideoSystemStatusDto(BaseModel):
    ffmpeg_available: bool
    ffmpeg_path: str | None = None
    public_api_base_url: str | None = None
    media_base_url: str
    media_backend: str = "local"
    providers: list[VideoProviderStatusDto]


class VideoSceneDto(BaseModel):
    id: UUID
    video_project_id: UUID
    sequence_index: int
    scene_type: VideoSceneType
    start_time_ms: int
    end_time_ms: int
    spoken_text: str | None
    on_screen_text: str | None
    visual_prompt: str | None
    transition: str
    metadata: dict[str, object]
    created_at: datetime
    updated_at: datetime


class VideoAssetDto(BaseModel):
    id: UUID
    workspace_id: UUID
    video_project_id: UUID
    video_scene_id: UUID | None = None
    asset_type: VideoAssetType
    source: VideoAssetSource
    status: VideoAssetStatus
    prompt: str | None = None
    provider: str | None = None
    provider_model: str | None = None
    provider_request_id: str | None = None
    provider_url: str | None = None
    storage_url: str | None = None
    cost_usd_ticks: int | None = None
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class RenderJobDto(BaseModel):
    id: UUID
    workspace_id: UUID
    video_render_id: UUID
    idempotency_key: str
    status: RenderJobStatus
    attempts: int
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class VideoRenderDto(BaseModel):
    id: UUID
    video_project_id: UUID
    workspace_id: UUID
    status: RenderStatus
    output_url: str | None = None
    error_message: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)
    jobs: list[RenderJobDto] = Field(default_factory=list)
    caption_tracks: list[CaptionTrackDto] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VideoProjectDto(BaseModel):
    id: UUID
    workspace_id: UUID
    parent_video_project_id: UUID | None = None
    variant_label: str | None = None
    title: str
    platform: VideoPlatform
    aspect_ratio: VideoAspectRatio
    target_duration_seconds: int
    status: VideoProjectStatus
    created_by_id: UUID | None
    metadata: dict[str, object] = Field(default_factory=dict)
    scenes: list[VideoSceneDto] = Field(default_factory=list)
    assets: list[VideoAssetDto] = Field(default_factory=list)
    renders: list[VideoRenderDto] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


__all__ = [
    "VideoPlatform",
    "VideoAspectRatio",
    "VideoProjectStatus",
    "VideoSceneType",
    "VideoTransition",
    "RenderStatus",
    "RenderJobStatus",
    "VideoAssetType",
    "VideoAssetSource",
    "VideoAssetStatus",
    "XaiImageResolution",
    "XaiVideoResolution",
    "CaptionTrackDto",
    "VideoProviderStatusDto",
    "VideoSystemStatusDto",
    "VideoSceneDto",
    "VideoAssetDto",
    "RenderJobDto",
    "VideoRenderDto",
    "VideoProjectDto",
]
