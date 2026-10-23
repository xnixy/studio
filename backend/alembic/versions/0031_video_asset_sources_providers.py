"""Allow gemini and seedance as video_assets.source values.

Revision ID: 0031_video_asset_sources
Revises: 0030_solo_account
"""
from alembic import op

revision = "0031_video_asset_sources"
down_revision = "0030_solo_account"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_video_assets_source", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_source",
        "video_assets",
        "source in ('xai', 'sync_labs', 'gemini', 'seedance', 'upload', 'stock', 'render', 'system')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_video_assets_source", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_source",
        "video_assets",
        "source in ('xai', 'sync_labs', 'upload', 'stock', 'render', 'system')",
    )
