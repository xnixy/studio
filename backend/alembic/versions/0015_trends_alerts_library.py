"""trend entities, alert subscriptions/events, winning library items

Revision ID: 0015_trends_alerts_library
Revises: 0014_performance_metrics
Create Date: 2026-07-11 04:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015_trends_alerts_library"
down_revision = "0014_performance_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trend_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(length=48), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("platform", sa.String(length=48), nullable=True),
        sa.Column("window_start", sa.Date(), nullable=False),
        sa.Column("window_end", sa.Date(), nullable=False),
        sa.Column("frequency", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("recency", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("acceleration", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("saturation", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("composite", sa.Numeric(8, 2), nullable=False, server_default="0"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("competitor_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ad_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uncertainty", sa.String(length=64), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "entity_type in ('hook_type', 'angle', 'cta', 'platform', 'visual_format')",
            name="ck_trend_entities_type",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "entity_type",
            "label",
            "window_end",
            "platform",
            name="uq_trend_entities_window_label",
        ),
    )
    op.create_index(op.f("ix_trend_entities_workspace_id"), "trend_entities", ["workspace_id"], unique=False)
    op.create_index("ix_trend_entities_workspace_window", "trend_entities", ["workspace_id", "window_end"], unique=False)
    op.create_index("ix_trend_entities_composite", "trend_entities", ["workspace_id", "composite"], unique=False)

    op.create_table(
        "alert_subscriptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=160), nullable=False, server_default="Weekly intelligence"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("channels", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[\"in_app\"]'::jsonb")),
        sa.Column("email_recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("filters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_alert_subscriptions_workspace_id"), "alert_subscriptions", ["workspace_id"], unique=False)

    op.create_table(
        "alert_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subscription_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("alert_subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_type", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "event_type in ('competitor_change', 'rising_pattern', 'declining_trend', 'recommended_test')",
            name="ck_alert_events_type",
        ),
        sa.CheckConstraint(
            "delivery_status in ('pending', 'in_app', 'sent', 'failed', 'skipped')",
            name="ck_alert_events_delivery",
        ),
    )
    op.create_index(op.f("ix_alert_events_workspace_id"), "alert_events", ["workspace_id"], unique=False)
    op.create_index("ix_alert_events_created", "alert_events", ["workspace_id", "created_at"], unique=False)

    op.create_table(
        "library_items",
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
        sa.Column("item_type", sa.String(length=48), nullable=False, server_default="hook"),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("platform", sa.String(length=48), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="candidate"),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("source", sa.String(length=48), nullable=False, server_default="manual"),
        sa.Column("source_metric_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("hook_text", sa.String(length=400), nullable=True),
        sa.Column("angle_text", sa.String(length=400), nullable=True),
        sa.Column("cta_text", sa.String(length=400), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "item_type in ('hook', 'opening', 'script', 'cta', 'caption_style', 'format', 'angle')",
            name="ck_library_items_type",
        ),
        sa.CheckConstraint(
            "status in ('candidate', 'proven', 'retired', 'rejected')",
            name="ck_library_items_status",
        ),
        sa.CheckConstraint("confidence between 0 and 100", name="ck_library_items_confidence"),
        sa.CheckConstraint("usage_count >= 0", name="ck_library_items_usage"),
    )
    op.create_index(op.f("ix_library_items_workspace_id"), "library_items", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_library_items_status"), "library_items", ["status"], unique=False)
    op.create_index("ix_library_items_workspace_type", "library_items", ["workspace_id", "item_type"], unique=False)


def downgrade() -> None:
    op.drop_table("library_items")
    op.drop_table("alert_events")
    op.drop_table("alert_subscriptions")
    op.drop_table("trend_entities")
