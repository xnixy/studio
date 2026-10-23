"""connect mvp1 creative data to the mvp2 platform layer

Revision ID: 0005_connect_mvp1_mvp2
Revises: 0004_mvp2_growth_layer
Create Date: 2026-07-10 12:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_connect_mvp1_mvp2"
down_revision = "0004_mvp2_growth_layer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workspaces", sa.Column("billing_workspace_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("workspaces", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.create_foreign_key(
        "fk_workspaces_billing_workspace_id",
        "workspaces",
        "workspaces",
        ["billing_workspace_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_workspaces_billing_workspace_id", "workspaces", ["billing_workspace_id"])
    op.execute("UPDATE workspaces SET billing_workspace_id = id WHERE billing_workspace_id IS NULL")
    op.create_check_constraint("ck_workspaces_type", "workspaces", "type in ('brand', 'agency')")

    # Guarantee every existing user has a workspace before project backfill.
    op.execute(
        """
        INSERT INTO workspaces (id, name, type, created_by_id, created_at, updated_at, billing_workspace_id)
        SELECT gen_random_uuid(), 'Personal workspace', 'brand', u.id, now(), now(), NULL
        FROM users u
        WHERE NOT EXISTS (SELECT 1 FROM workspace_members wm WHERE wm.user_id = u.id)
        """
    )
    op.execute("UPDATE workspaces SET billing_workspace_id = id WHERE billing_workspace_id IS NULL")
    op.alter_column("workspaces", "billing_workspace_id", nullable=False)
    op.execute(
        """
        INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at)
        SELECT gen_random_uuid(), w.id, w.created_by_id, 'owner', now()
        FROM workspaces w
        WHERE NOT EXISTS (
            SELECT 1 FROM workspace_members wm
            WHERE wm.workspace_id = w.id AND wm.user_id = w.created_by_id
        )
        """
    )
    op.execute(
        """
        INSERT INTO subscriptions (id, workspace_id, plan, status, created_at)
        SELECT gen_random_uuid(), w.id, 'free', 'active', now()
        FROM workspaces w
        WHERE w.billing_workspace_id = w.id
          AND NOT EXISTS (SELECT 1 FROM subscriptions s WHERE s.workspace_id = w.id)
        """
    )

    op.add_column("ad_projects", sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.execute(
        """
        UPDATE ad_projects p
        SET workspace_id = chosen.workspace_id
        FROM (
            SELECT DISTINCT ON (wm.user_id) wm.user_id, wm.workspace_id
            FROM workspace_members wm
            JOIN workspaces w ON w.id = wm.workspace_id
            ORDER BY wm.user_id, w.created_at, w.id
        ) chosen
        WHERE chosen.user_id = p.owner_id
        """
    )
    op.alter_column("ad_projects", "workspace_id", nullable=False)
    op.create_foreign_key("fk_ad_projects_workspace_id", "ad_projects", "workspaces", ["workspace_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_ad_projects_workspace_id", "ad_projects", ["workspace_id"])

    op.create_unique_constraint("uq_workspace_members_workspace_user", "workspace_members", ["workspace_id", "user_id"])
    op.create_check_constraint("ck_workspace_members_role", "workspace_members", "role in ('owner', 'admin', 'editor', 'viewer')")

    op.create_table(
        "workspace_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="editor"),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("role in ('admin', 'editor', 'viewer')", name="ck_workspace_invitations_role"),
    )
    op.create_index("ix_workspace_invitations_workspace_id", "workspace_invitations", ["workspace_id"])
    op.create_index("ix_workspace_invitations_email", "workspace_invitations", ["email"])
    op.create_index("ix_workspace_invitations_token_hash", "workspace_invitations", ["token_hash"], unique=True)

    op.add_column("competitor_observations", sa.Column("generated_project_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_competitor_observations_generated_project_id",
        "competitor_observations",
        "ad_projects",
        ["generated_project_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column("trend_watchlists", sa.Column("email_delivery_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column(
        "trend_watchlists",
        sa.Column("email_recipients", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
    )
    op.add_column("trend_reports", sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"))
    op.add_column("trend_reports", sa.Column("delivery_status", sa.String(length=32), nullable=False, server_default="not_requested"))
    op.add_column("trend_reports", sa.Column("error_message", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_trend_reports_watchlist_week", "trend_reports", ["watchlist_id", "week_start"])

    op.add_column("subscriptions", sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("subscriptions", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("usage_events", sa.Column("status", sa.String(length=24), nullable=False, server_default="consumed"))
    op.create_check_constraint("ck_usage_events_quantity_positive", "usage_events", "quantity > 0")
    op.create_check_constraint("ck_usage_events_status", "usage_events", "status in ('reserved', 'consumed', 'released')")

    op.create_table(
        "stripe_events",
        sa.Column("id", sa.String(length=255), primary_key=True),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_workspace_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("stripe_events")
    op.drop_constraint("ck_usage_events_status", "usage_events", type_="check")
    op.drop_constraint("ck_usage_events_quantity_positive", "usage_events", type_="check")
    op.drop_column("usage_events", "status")
    op.drop_column("subscriptions", "updated_at")
    op.drop_column("subscriptions", "cancel_at_period_end")
    op.drop_constraint("uq_trend_reports_watchlist_week", "trend_reports", type_="unique")
    op.drop_column("trend_reports", "error_message")
    op.drop_column("trend_reports", "delivery_status")
    op.drop_column("trend_reports", "status")
    op.drop_column("trend_watchlists", "email_recipients")
    op.drop_column("trend_watchlists", "email_delivery_enabled")
    op.drop_constraint("fk_competitor_observations_generated_project_id", "competitor_observations", type_="foreignkey")
    op.drop_column("competitor_observations", "generated_project_id")
    op.drop_index("ix_workspace_invitations_token_hash", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_email", table_name="workspace_invitations")
    op.drop_index("ix_workspace_invitations_workspace_id", table_name="workspace_invitations")
    op.drop_table("workspace_invitations")
    op.drop_constraint("ck_workspace_members_role", "workspace_members", type_="check")
    op.drop_constraint("uq_workspace_members_workspace_user", "workspace_members", type_="unique")
    op.drop_index("ix_ad_projects_workspace_id", table_name="ad_projects")
    op.drop_constraint("fk_ad_projects_workspace_id", "ad_projects", type_="foreignkey")
    op.drop_column("ad_projects", "workspace_id")
    op.drop_constraint("ck_workspaces_type", "workspaces", type_="check")
    op.drop_index("ix_workspaces_billing_workspace_id", table_name="workspaces")
    op.drop_constraint("fk_workspaces_billing_workspace_id", "workspaces", type_="foreignkey")
    op.drop_column("workspaces", "updated_at")
    op.drop_column("workspaces", "billing_workspace_id")
