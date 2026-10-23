"""voiceover assets

Revision ID: 0003_voiceover_assets
Revises: 0002_ad_creative_mvp
Create Date: 2026-07-09 17:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_voiceover_assets"
down_revision = "0002_ad_creative_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "voiceover_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("concept_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("ad_concepts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("voice", sa.String(length=32), nullable=False),
        sa.Column("tone", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="provider_required"),
        sa.Column("estimated_seconds", sa.Integer(), nullable=False),
        sa.Column("credits_used", sa.Integer(), nullable=False),
        sa.Column("download_url", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_voiceover_assets_concept_id", "voiceover_assets", ["concept_id"])


def downgrade() -> None:
    op.drop_index("ix_voiceover_assets_concept_id", table_name="voiceover_assets")
    op.drop_table("voiceover_assets")
