"""video project foundation

Revision ID: 0007_video_projects
Revises: 0006_platform_hardening
Create Date: 2026-07-10 14:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_video_projects"
down_revision = "0006_platform_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_concept_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ad_concepts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("platform", sa.String(length=32), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False, server_default="9:16"),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("platform in ('tiktok', 'instagram_reels', 'youtube_shorts', 'meta_feed', 'meta_story')", name="ck_video_projects_platform"),
        sa.CheckConstraint("aspect_ratio in ('9:16', '1:1', '4:5')", name="ck_video_projects_aspect_ratio"),
        sa.CheckConstraint("target_duration_seconds in (15, 30, 45, 60)", name="ck_video_projects_target_duration"),
        sa.CheckConstraint("status in ('draft', 'ready', 'rendering', 'complete', 'failed', 'archived')", name="ck_video_projects_status"),
    )
    op.create_index("ix_video_projects_workspace_id", "video_projects", ["workspace_id"])
    op.create_index("ix_video_projects_source_concept_id", "video_projects", ["source_concept_id"])

    op.create_table(
        "video_scenes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("video_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("scene_type", sa.String(length=32), nullable=False, server_default="storyboard"),
        sa.Column("start_time_ms", sa.Integer(), nullable=False),
        sa.Column("end_time_ms", sa.Integer(), nullable=False),
        sa.Column("spoken_text", sa.Text(), nullable=True),
        sa.Column("on_screen_text", sa.Text(), nullable=True),
        sa.Column("visual_prompt", sa.Text(), nullable=True),
        sa.Column("transition", sa.String(length=32), nullable=False, server_default="cut"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("sequence_index >= 0", name="ck_video_scenes_sequence_nonnegative"),
        sa.CheckConstraint("start_time_ms >= 0", name="ck_video_scenes_start_nonnegative"),
        sa.CheckConstraint("end_time_ms > start_time_ms", name="ck_video_scenes_end_after_start"),
        sa.CheckConstraint("scene_type in ('storyboard', 'product', 'text_card', 'end_card')", name="ck_video_scenes_type"),
        sa.UniqueConstraint("video_project_id", "sequence_index", name="uq_video_scenes_project_sequence"),
    )
    op.create_index("ix_video_scenes_video_project_id", "video_scenes", ["video_project_id"])

    op.create_table(
        "video_renders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("video_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("output_url", sa.String(length=1000), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("render_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status in ('queued', 'processing', 'rendering', 'uploading', 'complete', 'failed', 'canceled')", name="ck_video_renders_status"),
    )
    op.create_index("ix_video_renders_video_project_id", "video_renders", ["video_project_id"])
    op.create_index("ix_video_renders_workspace_id", "video_renders", ["workspace_id"])

    op.create_table(
        "render_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_render_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_renders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("idempotency_key", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("job_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status in ('queued', 'processing', 'waiting_for_provider', 'rendering', 'uploading', 'complete', 'failed', 'canceled')", name="ck_render_jobs_status"),
        sa.CheckConstraint("attempts >= 0", name="ck_render_jobs_attempts_nonnegative"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_render_jobs_workspace_idempotency"),
    )
    op.create_index("ix_render_jobs_workspace_id", "render_jobs", ["workspace_id"])
    op.create_index("ix_render_jobs_video_render_id", "render_jobs", ["video_render_id"])


def downgrade() -> None:
    op.drop_index("ix_render_jobs_video_render_id", table_name="render_jobs")
    op.drop_index("ix_render_jobs_workspace_id", table_name="render_jobs")
    op.drop_table("render_jobs")
    op.drop_index("ix_video_renders_workspace_id", table_name="video_renders")
    op.drop_index("ix_video_renders_video_project_id", table_name="video_renders")
    op.drop_table("video_renders")
    op.drop_index("ix_video_scenes_video_project_id", table_name="video_scenes")
    op.drop_table("video_scenes")
    op.drop_index("ix_video_projects_source_concept_id", table_name="video_projects")
    op.drop_index("ix_video_projects_workspace_id", table_name="video_projects")
    op.drop_table("video_projects")
