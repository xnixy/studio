"""ad creative mvp

Revision ID: 0002_ad_creative_mvp
Revises: 0001_initial
Create Date: 2026-07-09 16:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_ad_creative_mvp"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ad_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_input", sa.Text(), nullable=False),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("benefits", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("niche", sa.String(length=240), nullable=False),
        sa.Column("pain_points", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("target_customer", sa.String(length=500), nullable=False),
        sa.Column("competitors", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("keywords", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("references", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ad_projects_owner_id", "ad_projects", ["owner_id"])

    op.create_table(
        "ad_concepts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ad_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_summary", sa.Text(), nullable=False),
        sa.Column("ad_angle", sa.Text(), nullable=False),
        sa.Column("pattern", sa.String(length=240), nullable=False),
        sa.Column("hook", sa.Text(), nullable=False),
        sa.Column("script", sa.Text(), nullable=False),
        sa.Column("storyboard", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("caption", sa.Text(), nullable=False),
        sa.Column("cta", sa.String(length=160), nullable=False),
        sa.Column("meta_ad_copy", sa.Text(), nullable=False),
        sa.Column("tiktok_ad_copy", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ad_concepts_project_id", "ad_concepts", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_ad_concepts_project_id", table_name="ad_concepts")
    op.drop_table("ad_concepts")
    op.drop_index("ix_ad_projects_owner_id", table_name="ad_projects")
    op.drop_table("ad_projects")
