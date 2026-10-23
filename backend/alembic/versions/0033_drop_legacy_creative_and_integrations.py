"""Drop ad creative graph, brand templates, integrations; strip legacy columns.

Revision ID: 0033_drop_legacy_creative
Revises: 0032_drop_retired_product_tables
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# Keep revision IDs <= 32 chars (alembic_version.version_num default).
revision = "0033_drop_legacy_creative"
down_revision = "0032_drop_retired_product_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FKs / columns on video_projects before dropping parent tables.
    op.execute(
        sa.text(
            """
            ALTER TABLE IF EXISTS video_projects
              DROP COLUMN IF EXISTS source_concept_id,
              DROP COLUMN IF EXISTS brand_template_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE IF EXISTS share_links
              DROP COLUMN IF EXISTS client_id
            """
        )
    )

    tables = [
        "voiceover_assets",
        "ad_concepts",
        "ad_projects",
        "brand_templates",
        "workspace_api_keys",
        "webhook_endpoints",
        "integration_connections",
    ]
    for name in tables:
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{name}" CASCADE'))

    op.execute(
        sa.text(
            """
            DELETE FROM background_jobs
            WHERE job_type IN ('webhook.deliver', 'integration.sync')
               OR job_type LIKE 'monitoring.%'
               OR job_type LIKE 'performance.%'
               OR job_type LIKE 'recommendation.%'
               OR job_type LIKE 'trend.%'
               OR job_type LIKE 'alert.%'
            """
        )
    )


def downgrade() -> None:
    # Legacy tables are not recreated. Restore from backup if needed.
    pass
