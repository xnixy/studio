"""transactional email: verify, reset tokens, invite recipient

Revision ID: 0023_transactional_email
Revises: 0022_client_invites
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023_transactional_email"
down_revision = "0022_client_invites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invite_codes", sa.Column("email", sa.String(length=256), nullable=True))
    op.add_column("invite_codes", sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_invite_codes_email", "invite_codes", ["email"])

    op.create_table(
        "auth_email_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("purpose in ('password_reset', 'email_verify')", name="ck_auth_email_tokens_purpose"),
        sa.UniqueConstraint("token_hash", name="uq_auth_email_tokens_token_hash"),
    )
    op.create_index("ix_auth_email_tokens_user_id", "auth_email_tokens", ["user_id"])
    op.create_index("ix_auth_email_tokens_token_hash", "auth_email_tokens", ["token_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_auth_email_tokens_token_hash", table_name="auth_email_tokens")
    op.drop_index("ix_auth_email_tokens_user_id", table_name="auth_email_tokens")
    op.drop_table("auth_email_tokens")
    op.drop_index("ix_invite_codes_email", table_name="invite_codes")
    op.drop_column("invite_codes", "email_sent_at")
    op.drop_column("invite_codes", "email")
    op.drop_column("users", "email_verified_at")
