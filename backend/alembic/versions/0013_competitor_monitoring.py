"""competitor monitoring targets, ads, sightings, landing snapshots

Revision ID: 0013_competitor_monitoring
Revises: 0012_background_jobs
Create Date: 2026-07-11 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013_competitor_monitoring"
down_revision = "0012_background_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monitored_competitors",
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
            "competitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("competitors.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("website_url", sa.String(length=1000), nullable=True),
        sa.Column("social_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("platforms", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("monitoring_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("scan_interval_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_config", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active', 'paused', 'error')", name="ck_monitored_competitors_status"),
        sa.CheckConstraint("scan_interval_hours >= 1", name="ck_monitored_competitors_scan_interval"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_monitored_competitors_workspace_name"),
    )
    op.create_index(op.f("ix_monitored_competitors_workspace_id"), "monitored_competitors", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_monitored_competitors_client_id"), "monitored_competitors", ["client_id"], unique=False)
    op.create_index(op.f("ix_monitored_competitors_competitor_id"), "monitored_competitors", ["competitor_id"], unique=False)
    # Partial unique: one monitoring target per research competitor when linked
    op.create_index(
        "uq_monitored_competitors_workspace_competitor",
        "monitored_competitors",
        ["workspace_id", "competitor_id"],
        unique=True,
        postgresql_where=sa.text("competitor_id IS NOT NULL"),
    )
    op.create_index(
        "ix_monitored_competitors_enabled",
        "monitored_competitors",
        ["workspace_id", "monitoring_enabled"],
        unique=False,
    )

    op.create_table(
        "competitor_ads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "monitored_competitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("monitored_competitors.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=240), nullable=False),
        sa.Column("dedupe_hash", sa.String(length=64), nullable=False),
        sa.Column("platform", sa.String(length=48), nullable=False, server_default="unknown"),
        sa.Column("hook_text", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("cta_text", sa.Text(), nullable=True),
        sa.Column("media_urls", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("landing_page_url", sa.String(length=1000), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("source_provider", sa.String(length=64), nullable=False, server_default="manual"),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("monitored_competitor_id", "dedupe_hash", name="uq_competitor_ads_target_dedupe"),
        sa.UniqueConstraint(
            "monitored_competitor_id",
            "source_provider",
            "external_id",
            name="uq_competitor_ads_target_provider_external",
        ),
    )
    op.create_index(op.f("ix_competitor_ads_workspace_id"), "competitor_ads", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_competitor_ads_monitored_competitor_id"), "competitor_ads", ["monitored_competitor_id"], unique=False)
    op.create_index("ix_competitor_ads_workspace_dedupe", "competitor_ads", ["workspace_id", "dedupe_hash"], unique=False)
    op.create_index("ix_competitor_ads_last_seen", "competitor_ads", ["monitored_competitor_id", "last_seen_at"], unique=False)

    op.create_table(
        "competitor_ad_sightings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ad_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("competitor_ads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "scan_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("background_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("landing_page_hash", sa.String(length=64), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_competitor_ad_sightings_workspace_id"), "competitor_ad_sightings", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_competitor_ad_sightings_ad_id"), "competitor_ad_sightings", ["ad_id"], unique=False)
    op.create_index("ix_competitor_ad_sightings_seen_at", "competitor_ad_sightings", ["ad_id", "seen_at"], unique=False)

    op.create_table(
        "landing_page_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "monitored_competitor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("monitored_competitors.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("diff_summary", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_landing_page_snapshots_workspace_id"), "landing_page_snapshots", ["workspace_id"], unique=False)
    op.create_index(
        op.f("ix_landing_page_snapshots_monitored_competitor_id"),
        "landing_page_snapshots",
        ["monitored_competitor_id"],
        unique=False,
    )
    op.create_index("ix_landing_page_snapshots_fetched", "landing_page_snapshots", ["fetched_at"], unique=False)


def downgrade() -> None:
    op.drop_table("landing_page_snapshots")
    op.drop_table("competitor_ad_sightings")
    op.drop_table("competitor_ads")
    op.drop_index("ix_monitored_competitors_enabled", table_name="monitored_competitors")
    op.drop_index("uq_monitored_competitors_workspace_competitor", table_name="monitored_competitors")
    op.drop_table("monitored_competitors")
