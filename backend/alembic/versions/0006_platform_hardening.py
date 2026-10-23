"""normalize billing roots and harden platform constraints

Revision ID: 0006_platform_hardening
Revises: 0005_connect_mvp1_mvp2
Create Date: 2026-07-10 13:00:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0006_platform_hardening"
down_revision = "0005_connect_mvp1_mvp2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH roots AS (
            SELECT DISTINCT ON (created_by_id) created_by_id, id AS root_id
            FROM workspaces
            ORDER BY created_by_id, created_at, id
        )
        UPDATE workspaces w
        SET billing_workspace_id = roots.root_id
        FROM roots
        WHERE roots.created_by_id = w.created_by_id
        """
    )
    op.execute("DELETE FROM subscriptions s USING workspaces w WHERE s.workspace_id = w.id AND w.billing_workspace_id <> w.id")

    op.drop_constraint("ad_projects_owner_id_fkey", "ad_projects", type_="foreignkey")
    op.alter_column("ad_projects", "owner_id", nullable=True)
    op.create_foreign_key("ad_projects_owner_id_fkey", "ad_projects", "users", ["owner_id"], ["id"], ondelete="SET NULL")
    op.create_check_constraint("ck_subscriptions_plan", "subscriptions", "plan in ('free', 'starter', 'pro', 'agency')")
    op.create_check_constraint(
        "ck_subscriptions_status",
        "subscriptions",
        "status in ('active', 'trialing', 'past_due', 'unpaid', 'paused', 'canceled', 'incomplete', 'incomplete_expired')",
    )
    op.create_check_constraint("ck_trend_reports_status", "trend_reports", "status in ('pending', 'completed', 'failed')")
    op.create_check_constraint("ck_trend_reports_delivery_status", "trend_reports", "delivery_status in ('not_requested', 'pending', 'sent', 'failed')")
    op.create_index("ix_usage_events_type_created_at", "usage_events", ["event_type", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_type_created_at", table_name="usage_events")
    op.drop_constraint("ck_trend_reports_delivery_status", "trend_reports", type_="check")
    op.drop_constraint("ck_trend_reports_status", "trend_reports", type_="check")
    op.drop_constraint("ck_subscriptions_status", "subscriptions", type_="check")
    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.drop_constraint("ad_projects_owner_id_fkey", "ad_projects", type_="foreignkey")
    op.alter_column("ad_projects", "owner_id", nullable=False)
    op.create_foreign_key("ad_projects_owner_id_fkey", "ad_projects", "users", ["owner_id"], ["id"], ondelete="CASCADE")
    op.execute("UPDATE workspaces SET billing_workspace_id = id")
