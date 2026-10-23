"""Allow kling as video_assets.source value.

Revision ID: 0035_kling_video_source
Revises: 0034_billing_addon_play
"""
from alembic import op

revision = "0035_kling_video_source"
down_revision = "0034_billing_addon_play"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_video_assets_source", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_source",
        "video_assets",
        "source in ('xai', 'sync_labs', 'gemini', 'seedance', 'kling', 'upload', 'stock', 'render', 'system')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_video_assets_source", "video_assets", type_="check")
    op.create_check_constraint(
        "ck_video_assets_source",
        "video_assets",
        "source in ('xai', 'sync_labs', 'gemini', 'seedance', 'upload', 'stock', 'render', 'system')",
    )
