"""Indexes for the usage_events reserve hot path.

Every reserve_usage call scans for stale reservations and sums prior usage.
usage_events is append-only and had only a workspace_id index, so both queries
degraded into full scans as the table grew.

Revision ID: 0039_usage_event_indexes
Revises: 0038_workspace_voices
"""
from alembic import op
import sqlalchemy as sa

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0039_usage_event_indexes"
down_revision = "0038_workspace_voices"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Stale-reservation sweep only ever looks at reserved rows, of which there
    # are a handful at any moment. Partial keeps the index tiny.
    op.create_index(
        "ix_usage_events_reserved_created_at",
        "usage_events",
        ["created_at"],
        unique=False,
        postgresql_where=sa.text("status = 'reserved'"),
    )
    # usage_total sums one workspace and event type over the current period.
    op.create_index(
        "ix_usage_events_workspace_event_created",
        "usage_events",
        ["workspace_id", "event_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_workspace_event_created", table_name="usage_events")
    op.drop_index("ix_usage_events_reserved_created_at", table_name="usage_events")
