"""Custom voice waitlist for admin-gated cloning access.

Revision ID: 0037_voice_waitlist
Revises: 0036_play_duration_range
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0037_voice_waitlist"
down_revision = "0036_play_duration_range"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voice_waitlist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("admin_note", sa.Text(), nullable=True),
        sa.Column(
            "reviewed_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("workspace_id", name="uq_voice_waitlist_workspace"),
        sa.CheckConstraint(
            "status in ('pending', 'approved', 'rejected')",
            name="ck_voice_waitlist_status",
        ),
    )
    op.create_index("ix_voice_waitlist_entries_user_id", "voice_waitlist_entries", ["user_id"])
    op.create_index(
        "ix_voice_waitlist_entries_workspace_id", "voice_waitlist_entries", ["workspace_id"]
    )
    op.create_index("ix_voice_waitlist_entries_status", "voice_waitlist_entries", ["status"])


def downgrade() -> None:
    op.drop_index("ix_voice_waitlist_entries_status", table_name="voice_waitlist_entries")
    op.drop_index("ix_voice_waitlist_entries_workspace_id", table_name="voice_waitlist_entries")
    op.drop_index("ix_voice_waitlist_entries_user_id", table_name="voice_waitlist_entries")
    op.drop_table("voice_waitlist_entries")
