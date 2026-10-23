"""iap transactions for App Store purchases

Revision ID: 0028_iap_transactions
Revises: 0027_device_push_tokens
Create Date: 2026-07-22
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0028_iap_transactions"
down_revision: Union[str, None] = "0027_device_push_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iap_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("transaction_id", sa.String(length=64), nullable=False),
        sa.Column("original_transaction_id", sa.String(length=64), nullable=True),
        sa.Column("apple_product_id", sa.String(length=120), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("sku", sa.String(length=48), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("environment", sa.String(length=16), nullable=False, server_default="Sandbox"),
        sa.Column("raw_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transaction_id", name="uq_iap_transactions_tx"),
    )
    op.create_index("ix_iap_transactions_workspace_id", "iap_transactions", ["workspace_id"])
    op.create_index("ix_iap_transactions_original_transaction_id", "iap_transactions", ["original_transaction_id"])


def downgrade() -> None:
    op.drop_index("ix_iap_transactions_original_transaction_id", table_name="iap_transactions")
    op.drop_index("ix_iap_transactions_workspace_id", table_name="iap_transactions")
    op.drop_table("iap_transactions")
