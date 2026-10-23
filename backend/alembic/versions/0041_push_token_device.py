"""One push token row per device, not per registration.

Tokens were unique on the token alone, so every reinstall, dev build, and Expo
Go session added another live row for the same phone and never removed one. A
finished clip then fanned out to all of them: one generation, ten notifications,
some of them arriving in Expo Go alongside the real app.

A device id makes registration an upsert, so a phone replaces its own row
instead of accumulating them. Rows predating this stay NULL and are treated as
one device each; the cleanup below removes the duplicates already stored.

Revision ID: 0041_push_token_device
Revises: 0040_refresh_token_family
"""
from alembic import op
import sqlalchemy as sa

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0041_push_token_device"
down_revision = "0040_refresh_token_family"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("device_push_tokens", sa.Column("device_id", sa.String(length=128), nullable=True))
    op.create_unique_constraint(
        "uq_device_push_tokens_user_device",
        "device_push_tokens",
        ["user_id", "device_id"],
    )
    # Existing rows carry no device id, so they cannot be deduped by one. They are
    # all live tokens for phones that have long since rotated, and the client
    # re-registers on next launch, so keep only the newest per user and platform.
    op.execute(
        """
        DELETE FROM device_push_tokens t
        USING device_push_tokens newer
        WHERE t.device_id IS NULL
          AND newer.device_id IS NULL
          AND t.user_id = newer.user_id
          AND t.platform = newer.platform
          AND t.updated_at < newer.updated_at
        """
    )


def downgrade() -> None:
    op.drop_constraint("uq_device_push_tokens_user_device", "device_push_tokens", type_="unique")
    op.drop_column("device_push_tokens", "device_id")
