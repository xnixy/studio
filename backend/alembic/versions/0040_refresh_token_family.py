"""Group refresh tokens into per-sign-in chains.

Replay detection revoked every session for the user, so one stale token on a
phone that lost a refresh response signed the same account out of the website
too. A family id ties each rotation chain back to the sign-in that started it,
letting a replay revoke only its own chain.

Existing rows stay NULL and are handled as a chain of one.

Revision ID: 0040_refresh_token_family
Revises: 0039_usage_event_indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0040_refresh_token_family"
down_revision = "0039_usage_event_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("family_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    # Revocation looks up a whole chain, so this is on the hot path of refresh.
    op.create_index(
        "ix_refresh_tokens_family_id",
        "refresh_tokens",
        ["family_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_refresh_tokens_family_id", table_name="refresh_tokens")
    op.drop_column("refresh_tokens", "family_id")
