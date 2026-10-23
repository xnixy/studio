"""sync labs avatar assets

Revision ID: 0009_sync_labs_avatar_assets
Revises: 0008_media_provider_assets
Create Date: 2026-07-10 16:30:00.000000
"""

from __future__ import annotations

from alembic import op

revision = "0009_sync_labs_avatar_assets"
down_revision = "0008_media_provider_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_video_assets_source", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_source",
        "video_assets",
        "source in ('xai', 'sync_labs', 'upload', 'stock', 'render', 'system')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_video_assets_source", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_source",
        "video_assets",
        "source in ('xai', 'upload', 'stock', 'render', 'system')",
    )
