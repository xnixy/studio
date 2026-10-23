"""Drop voice waitlist. Add clone gender/language. Allow elevenlabs provider.

Revision ID: 0042_voices_elevenlabs
Revises: 0041_push_token_device
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0042_voices_elevenlabs"
down_revision = "0041_push_token_device"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_voice_waitlist_entries_status", table_name="voice_waitlist_entries")
    op.drop_index("ix_voice_waitlist_entries_workspace_id", table_name="voice_waitlist_entries")
    op.drop_index("ix_voice_waitlist_entries_user_id", table_name="voice_waitlist_entries")
    op.drop_table("voice_waitlist_entries")

    op.add_column("workspace_voices", sa.Column("gender", sa.String(length=16), nullable=True))
    op.add_column("workspace_voices", sa.Column("language", sa.String(length=16), nullable=True))
    op.create_check_constraint(
        "ck_workspace_voices_provider",
        "workspace_voices",
        "provider in ('elevenlabs', 'xai')",
    )
    op.create_check_constraint(
        "ck_workspace_voices_gender",
        "workspace_voices",
        "gender is null or gender in ('female', 'male', 'neutral')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workspace_voices_gender", "workspace_voices", type_="check")
    op.drop_constraint("ck_workspace_voices_provider", "workspace_voices", type_="check")
    op.drop_column("workspace_voices", "language")
    op.drop_column("workspace_voices", "gender")
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
