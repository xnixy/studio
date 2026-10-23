"""Restrict billing_addons.addon_type to Play-era packs (drop monitored_competitors).

Revision ID: 0034_billing_addon_play
Revises: 0033_drop_legacy_creative
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0034_billing_addon_play"
down_revision = "0033_drop_legacy_creative"
branch_labels = None
depends_on = None

NEW_CHECK = (
    "addon_type in ("
    "'seats', 'video_credits', 'image_generations', 'avatar_lipsyncs', "
    "'script_generations', 'voiceover_minutes', 'storage_gb', 'priority_rendering'"
    ")"
)


def upgrade() -> None:
    # Cancel legacy competitor add-ons; they no longer map to a product surface.
    op.execute(
        sa.text(
            """
            UPDATE billing_addons
            SET status = 'canceled'
            WHERE addon_type = 'monitored_competitors'
              AND status = 'active'
            """
        )
    )
    op.execute(sa.text("ALTER TABLE billing_addons DROP CONSTRAINT IF EXISTS ck_billing_addons_type"))
    op.execute(
        sa.text(
            f"ALTER TABLE billing_addons ADD CONSTRAINT ck_billing_addons_type CHECK ({NEW_CHECK})"
        )
    )


def downgrade() -> None:
    old = (
        "addon_type in ("
        "'seats', 'monitored_competitors', 'video_credits', 'image_generations', "
        "'avatar_lipsyncs', 'script_generations', 'voiceover_minutes', 'storage_gb', 'priority_rendering'"
        ")"
    )
    op.execute(sa.text("ALTER TABLE billing_addons DROP CONSTRAINT IF EXISTS ck_billing_addons_type"))
    op.execute(sa.text(f"ALTER TABLE billing_addons ADD CONSTRAINT ck_billing_addons_type CHECK ({old})"))
