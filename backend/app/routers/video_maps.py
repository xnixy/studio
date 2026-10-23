"""DTO mappers for video router responses."""
from __future__ import annotations

from app.config import get_settings
from app.media_signing import ASSET_METADATA_MEDIA_KEYS, sign_media_fields, sign_media_url
from app.models import CaptionTrack, VideoAsset, VideoProject, VideoRender, VideoScene
from app.schemas import (
    CaptionTrackDto,
    VideoAssetDto,
    VideoProjectDto,
    VideoRenderDto,
    VideoSceneDto,
)
from app.routers.video_scene_plan import repair_scene


def _signed(url: str | None) -> str | None:
    return sign_media_url(url, get_settings())


def map_asset(asset: VideoAsset) -> VideoAssetDto:
    settings = get_settings()
    meta = sign_media_fields(
        dict(asset.asset_metadata or {}),
        settings,
        keys=ASSET_METADATA_MEDIA_KEYS,
    )
    return VideoAssetDto(
        id=asset.id,
        workspace_id=asset.workspace_id,
        video_project_id=asset.video_project_id,
        video_scene_id=asset.video_scene_id,
        asset_type=asset.asset_type,  # type: ignore[arg-type]
        source=asset.source,  # type: ignore[arg-type]
        status=asset.status,  # type: ignore[arg-type]
        prompt=asset.prompt,
        provider=asset.provider,
        provider_model=asset.provider_model,
        provider_request_id=asset.provider_request_id,
        provider_url=asset.provider_url,
        storage_url=sign_media_url(asset.storage_url, settings),
        cost_usd_ticks=asset.cost_usd_ticks,
        error_message=asset.error_message,
        metadata=meta,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def map_caption_track(track: CaptionTrack) -> CaptionTrackDto:
    return CaptionTrackDto(
        id=track.id,
        workspace_id=track.workspace_id,
        video_render_id=track.video_render_id,
        format=track.format,  # type: ignore[arg-type]
        language=track.language,
        url=_signed(track.url),
        burned_in=track.burned_in,
        metadata=dict(track.track_metadata or {}),
        created_at=track.created_at,
    )


def map_scene(scene: VideoScene) -> VideoSceneDto:
    return VideoSceneDto(
        id=scene.id,
        video_project_id=scene.video_project_id,
        sequence_index=scene.sequence_index,
        scene_type=scene.scene_type,  # type: ignore[arg-type]
        start_time_ms=scene.start_time_ms,
        end_time_ms=scene.end_time_ms,
        spoken_text=scene.spoken_text,
        on_screen_text=scene.on_screen_text,
        visual_prompt=scene.visual_prompt,
        transition=scene.transition,
        metadata=dict(scene.scene_metadata or {}),
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


def map_render(render: VideoRender) -> VideoRenderDto:
    jobs = sorted(render.jobs, key=lambda item: item.created_at, reverse=True)
    caption_tracks = sorted(render.caption_tracks, key=lambda item: item.format) if hasattr(render, "caption_tracks") else []
    return VideoRenderDto(
        id=render.id,
        video_project_id=render.video_project_id,
        workspace_id=render.workspace_id,
        status=render.status,  # type: ignore[arg-type]
        output_url=_signed(render.output_url),
        error_message=render.error_message,
        metadata=dict(render.render_metadata or {}),
        caption_tracks=[map_caption_track(track) for track in caption_tracks],
        jobs=[
            {
                "id": job.id,
                "workspace_id": job.workspace_id,
                "video_render_id": job.video_render_id,
                "idempotency_key": job.idempotency_key,
                "status": job.status,
                "attempts": job.attempts,
                "error_message": job.error_message,
                "metadata": dict(job.job_metadata or {}),
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
            for job in jobs
        ],
        created_at=render.created_at,
        updated_at=render.updated_at,
    )


def map_project(project: VideoProject) -> VideoProjectDto:
    scenes = sorted(project.scenes, key=lambda item: item.sequence_index)
    for scene in scenes:
        repair_scene(scene)
    renders = sorted(project.renders, key=lambda item: item.created_at, reverse=True)
    assets = sorted(project.assets, key=lambda item: item.created_at, reverse=True)
    return VideoProjectDto(
        id=project.id,
        workspace_id=project.workspace_id,
        parent_video_project_id=project.parent_video_project_id,
        variant_label=project.variant_label,
        title=project.title,
        platform=project.platform,  # type: ignore[arg-type]
        aspect_ratio=project.aspect_ratio,  # type: ignore[arg-type]
        target_duration_seconds=project.target_duration_seconds,
        status=project.status,  # type: ignore[arg-type]
        created_by_id=project.created_by_id,
        metadata=dict(project.project_metadata or {}),
        scenes=[map_scene(scene) for scene in scenes],
        assets=[map_asset(asset) for asset in assets],
        renders=[map_render(render) for render in renders],
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


__all__ = [
    "map_asset",
    "map_caption_track",
    "map_scene",
    "map_render",
    "map_project",
]
