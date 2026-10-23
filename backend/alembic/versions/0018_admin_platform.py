"""Platform admin fields: user disable, last login, contact resolved

Revision ID: 0018_admin_platform
Revises: 0017_integrations
Create Date: 2026-07-10 23:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0018_admin_platform"
down_revision = "0017_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("is_disabled", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("contact_messages", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("contact_messages", "resolved_at")
    op.drop_column("users", "last_login_at")
    op.drop_column("users", "is_disabled")
