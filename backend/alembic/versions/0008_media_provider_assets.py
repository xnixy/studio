"""media provider assets

Revision ID: 0008_media_provider_assets
Revises: 0007_video_projects
Create Date: 2026-07-10 15:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_media_provider_assets"
down_revision = "0007_video_projects"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "video_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_scene_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_scenes.id", ondelete="CASCADE"), nullable=True),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="xai"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_model", sa.String(length=80), nullable=True),
        sa.Column("provider_request_id", sa.String(length=160), nullable=True),
        sa.Column("provider_url", sa.String(length=1000), nullable=True),
        sa.Column("storage_url", sa.String(length=1000), nullable=True),
        sa.Column("cost_usd_ticks", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("asset_type in ('image', 'video', 'audio', 'stock', 'upload', 'render', 'text_card')", name="ck_video_assets_type"),
        sa.CheckConstraint("source in ('xai', 'upload', 'stock', 'render', 'system')", name="ck_video_assets_source"),
        sa.CheckConstraint("status in ('queued', 'processing', 'ready', 'failed', 'expired')", name="ck_video_assets_status"),
    )
    op.create_index("ix_video_assets_workspace_id", "video_assets", ["workspace_id"])
    op.create_index("ix_video_assets_video_project_id", "video_assets", ["video_project_id"])
    op.create_index("ix_video_assets_video_scene_id", "video_assets", ["video_scene_id"])
    op.create_index("ix_video_assets_provider_request_id", "video_assets", ["provider_request_id"])

    op.create_table(
        "generation_costs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("feature", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_model", sa.String(length=80), nullable=True),
        sa.Column("provider_request_id", sa.String(length=160), nullable=True),
        sa.Column("cost_usd_ticks", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("cost_usd_ticks >= 0", name="ck_generation_costs_ticks_nonnegative"),
    )
    op.create_index("ix_generation_costs_workspace_id", "generation_costs", ["workspace_id"])
    op.create_index("ix_generation_costs_user_id", "generation_costs", ["user_id"])
    op.create_index("ix_generation_costs_provider_request_id", "generation_costs", ["provider_request_id"])


def downgrade() -> None:
    op.drop_index("ix_generation_costs_provider_request_id", table_name="generation_costs")
    op.drop_index("ix_generation_costs_user_id", table_name="generation_costs")
    op.drop_index("ix_generation_costs_workspace_id", table_name="generation_costs")
    op.drop_table("generation_costs")
    op.drop_index("ix_video_assets_provider_request_id", table_name="video_assets")
    op.drop_index("ix_video_assets_video_scene_id", table_name="video_assets")
    op.drop_index("ix_video_assets_video_project_id", table_name="video_assets")
    op.drop_index("ix_video_assets_workspace_id", table_name="video_assets")
    op.drop_table("video_assets")
