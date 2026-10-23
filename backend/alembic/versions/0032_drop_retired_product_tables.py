"""Drop retired product tables (brand, image ads, library, creative variants)

Revision ID: 0032_drop_retired_product_tables
Revises: 0031_video_asset_sources
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0032_drop_retired_product_tables"
down_revision = "0031_video_asset_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Child → parent. CASCADE covers leftover FKs from already-removed ads OS tables.
    tables = [
        "image_creatives",
        "image_packs",
        "brand_compliance_checks",
        "brand_facts",
        "brand_profiles",
        "library_items",
        "creative_variants",
    ]
    for name in tables:
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{name}" CASCADE'))

    # Job types that no longer have handlers or API surface.
    op.execute(
        sa.text(
            """
            DELETE FROM background_jobs
            WHERE job_type IN (
                'integration.sync',
                'monitoring.scan',
                'monitoring.landing_fetch',
                'performance.import',
                'recommendation.run',
                'trend.score',
                'alert.digest'
            )
            """
        )
    )


def downgrade() -> None:
    # Retired tables are not recreated. Restore from backup if needed.
    pass
