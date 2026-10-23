"""Workspace cloned voices (xAI custom voice ids).

Revision ID: 0038_workspace_voices
Revises: 0037_voice_waitlist
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0038_workspace_voices"
down_revision = "0037_voice_waitlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workspace_voices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False, server_default="xai"),
        sa.Column("provider_voice_id", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="cloned"),
        sa.Column("consent_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ready"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
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
        sa.CheckConstraint(
            "status in ('ready', 'failed', 'deleted')",
            name="ck_workspace_voices_status",
        ),
        sa.CheckConstraint(
            "source in ('cloned')",
            name="ck_workspace_voices_source",
        ),
    )
    op.create_index("ix_workspace_voices_workspace_id", "workspace_voices", ["workspace_id"])
    op.create_index("ix_workspace_voices_status", "workspace_voices", ["status"])
    op.create_index(
        "ix_workspace_voices_provider_voice_id", "workspace_voices", ["provider_voice_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_workspace_voices_provider_voice_id", table_name="workspace_voices")
    op.drop_index("ix_workspace_voices_status", table_name="workspace_voices")
    op.drop_index("ix_workspace_voices_workspace_id", table_name="workspace_voices")
    op.drop_table("workspace_voices")
