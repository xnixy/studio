"""mvp2 completion tables

Revision ID: 0010_mvp2_completion
Revises: 0009_sync_labs_avatar_assets
Create Date: 2026-07-10 19:15:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010_mvp2_completion"
down_revision = "0009_sync_labs_avatar_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("logo_url", sa.String(length=1000), nullable=True),
        sa.Column("primary_color", sa.String(length=24), nullable=False, server_default="#111827"),
        sa.Column("secondary_color", sa.String(length=24), nullable=False, server_default="#f9fafb"),
        sa.Column("accent_color", sa.String(length=24), nullable=False, server_default="#22c55e"),
        sa.Column("font_family", sa.String(length=120), nullable=False, server_default="Inter"),
        sa.Column("watermark_text", sa.String(length=120), nullable=True),
        sa.Column("caption_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("end_card_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cta_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("safe_zone_top_pct", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("safe_zone_bottom_pct", sa.Integer(), nullable=False, server_default="16"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("safe_zone_top_pct between 0 and 40", name="ck_brand_templates_safe_top"),
        sa.CheckConstraint("safe_zone_bottom_pct between 0 and 40", name="ck_brand_templates_safe_bottom"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_brand_templates_workspace_name"),
    )
    op.create_index(op.f("ix_brand_templates_workspace_id"), "brand_templates", ["workspace_id"], unique=False)

    op.add_column("video_projects", sa.Column("brand_template_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("video_projects", sa.Column("parent_video_project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("video_projects", sa.Column("variant_label", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_video_projects_brand_template_id"), "video_projects", ["brand_template_id"], unique=False)
    op.create_index(op.f("ix_video_projects_parent_video_project_id"), "video_projects", ["parent_video_project_id"], unique=False)
    op.create_foreign_key("fk_video_projects_brand_template_id", "video_projects", "brand_templates", ["brand_template_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_video_projects_parent_video_project_id", "video_projects", "video_projects", ["parent_video_project_id"], ["id"], ondelete="SET NULL")

    op.create_table(
        "caption_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("video_render_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_renders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False, server_default="en"),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("burned_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("format in ('vtt', 'srt', 'ass', 'burn_in')", name="ck_caption_tracks_format"),
        sa.UniqueConstraint("video_render_id", "format", "language", name="uq_caption_tracks_render_format_language"),
    )
    op.create_index(op.f("ix_caption_tracks_video_render_id"), "caption_tracks", ["video_render_id"], unique=False)
    op.create_index(op.f("ix_caption_tracks_workspace_id"), "caption_tracks", ["workspace_id"], unique=False)

    op.create_table(
        "creative_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_video_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_video_project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("variant_type", sa.String(length=48), nullable=False, server_default="platform_duration"),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('draft', 'ready', 'archived')", name="ck_creative_variants_status"),
        sa.CheckConstraint("variant_type in ('platform_duration', 'hook', 'scene_order', 'brand_template', 'manual')", name="ck_creative_variants_type"),
        sa.UniqueConstraint("variant_video_project_id", name="uq_creative_variants_variant_video_project_id"),
    )
    op.create_index(op.f("ix_creative_variants_source_video_project_id"), "creative_variants", ["source_video_project_id"], unique=False)
    op.create_index(op.f("ix_creative_variants_variant_video_project_id"), "creative_variants", ["variant_video_project_id"], unique=True)
    op.create_index(op.f("ix_creative_variants_workspace_id"), "creative_variants", ["workspace_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_creative_variants_workspace_id"), table_name="creative_variants")
    op.drop_index(op.f("ix_creative_variants_variant_video_project_id"), table_name="creative_variants")
    op.drop_index(op.f("ix_creative_variants_source_video_project_id"), table_name="creative_variants")
    op.drop_table("creative_variants")

    op.drop_index(op.f("ix_caption_tracks_workspace_id"), table_name="caption_tracks")
    op.drop_index(op.f("ix_caption_tracks_video_render_id"), table_name="caption_tracks")
    op.drop_table("caption_tracks")

    op.drop_constraint("fk_video_projects_parent_video_project_id", "video_projects", type_="foreignkey")
    op.drop_constraint("fk_video_projects_brand_template_id", "video_projects", type_="foreignkey")
    op.drop_index(op.f("ix_video_projects_parent_video_project_id"), table_name="video_projects")
    op.drop_index(op.f("ix_video_projects_brand_template_id"), table_name="video_projects")
    op.drop_column("video_projects", "variant_label")
    op.drop_column("video_projects", "parent_video_project_id")
    op.drop_column("video_projects", "brand_template_id")

    op.drop_index(op.f("ix_brand_templates_workspace_id"), table_name="brand_templates")
    op.drop_table("brand_templates")
