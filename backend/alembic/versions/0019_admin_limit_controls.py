"""admin limit and permission controls

Revision ID: 0019_admin_limit_controls
Revises: 0018_admin_platform
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019_admin_limit_controls"
down_revision = "0018_admin_platform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("limit_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.add_column(
        "workspace_members",
        sa.Column("permission_overrides", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )


def downgrade() -> None:
    op.drop_column("workspace_members", "permission_overrides")
    op.drop_column("subscriptions", "limit_overrides")
