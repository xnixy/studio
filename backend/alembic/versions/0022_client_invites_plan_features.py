"""client access invitations for agency invites

Revision ID: 0022_client_invites
Revises: 0021_credit_packs
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0022_client_invites"
down_revision = "0021_credit_packs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_access_invitations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="client"),
        sa.Column("can_approve", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_comment", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_view_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("invited_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("role in ('strategist', 'client', 'collaborator')", name="ck_client_access_invitations_role"),
        sa.UniqueConstraint("token_hash", name="uq_client_access_invitations_token"),
    )
    op.create_index("ix_client_access_invitations_client_id", "client_access_invitations", ["client_id"])
    op.create_index("ix_client_access_invitations_workspace_id", "client_access_invitations", ["workspace_id"])
    op.create_index("ix_client_access_invitations_email", "client_access_invitations", ["email"])


def downgrade() -> None:
    op.drop_index("ix_client_access_invitations_email", table_name="client_access_invitations")
    op.drop_index("ix_client_access_invitations_workspace_id", table_name="client_access_invitations")
    op.drop_index("ix_client_access_invitations_client_id", table_name="client_access_invitations")
    op.drop_table("client_access_invitations")
