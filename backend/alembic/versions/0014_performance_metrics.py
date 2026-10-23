"""performance CSV imports and metric facts

Revision ID: 0014_performance_metrics
Revises: 0013_competitor_monitoring
Create Date: 2026-07-11 02:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014_performance_metrics"
down_revision = "0013_competitor_monitoring"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "performance_imports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "brand_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="csv"),
        sa.Column("filename", sa.String(length=260), nullable=False),
        sa.Column("storage_key", sa.String(length=1000), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="uploaded"),
        sa.Column("column_mapping", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("detected", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("default_currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reverted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('uploaded', 'previewed', 'committing', 'committed', 'reverted', 'failed')",
            name="ck_performance_imports_status",
        ),
        sa.CheckConstraint("source in ('csv', 'meta_ads', 'tiktok_ads')", name="ck_performance_imports_source"),
    )
    op.create_index(op.f("ix_performance_imports_workspace_id"), "performance_imports", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_performance_imports_client_id"), "performance_imports", ["client_id"], unique=False)
    op.create_index(op.f("ix_performance_imports_status"), "performance_imports", ["status"], unique=False)

    op.create_table(
        "performance_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "import_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("performance_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_date", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("spend", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("impressions", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("clicks", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("views", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("hold_rate", sa.Numeric(8, 6), nullable=True),
        sa.Column("completion_rate", sa.Numeric(8, 6), nullable=True),
        sa.Column("purchases", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("revenue", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("cpa", sa.Numeric(18, 4), nullable=True),
        sa.Column("roas", sa.Numeric(18, 6), nullable=True),
        sa.Column(
            "brand_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("product_key", sa.String(length=160), nullable=True),
        sa.Column("campaign_name", sa.String(length=240), nullable=True),
        sa.Column("ad_name", sa.String(length=240), nullable=True),
        sa.Column("ad_external_id", sa.String(length=160), nullable=True),
        sa.Column(
            "ad_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "ad_concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_concepts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "video_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("video_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("variant_label", sa.String(length=120), nullable=True),
        sa.Column("experiment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hook_text", sa.String(length=400), nullable=True),
        sa.Column("angle_text", sa.String(length=400), nullable=True),
        sa.Column("platform", sa.String(length=48), nullable=True),
        sa.Column("row_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "row_fingerprint", name="uq_performance_metrics_workspace_fingerprint"),
    )
    op.create_index(op.f("ix_performance_metrics_workspace_id"), "performance_metrics", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_performance_metrics_import_id"), "performance_metrics", ["import_id"], unique=False)
    op.create_index("ix_performance_metrics_workspace_date", "performance_metrics", ["workspace_id", "metric_date"], unique=False)
    op.create_index(
        "ix_performance_metrics_workspace_brand_date",
        "performance_metrics",
        ["workspace_id", "brand_profile_id", "metric_date"],
        unique=False,
    )
    op.create_index(
        "ix_performance_metrics_workspace_hook",
        "performance_metrics",
        ["workspace_id", "hook_text"],
        unique=False,
        postgresql_where=sa.text("hook_text IS NOT NULL"),
    )
    op.create_index(
        "ix_performance_metrics_workspace_concept",
        "performance_metrics",
        ["workspace_id", "ad_concept_id"],
        unique=False,
        postgresql_where=sa.text("ad_concept_id IS NOT NULL"),
    )
    op.create_index(
        "ix_performance_metrics_workspace_experiment",
        "performance_metrics",
        ["workspace_id", "experiment_id"],
        unique=False,
        postgresql_where=sa.text("experiment_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_table("performance_metrics")
    op.drop_table("performance_imports")
