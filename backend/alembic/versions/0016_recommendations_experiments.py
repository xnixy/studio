"""recommendations and closed-loop experiments

Revision ID: 0016_recommendations_experiments
Revises: 0015_trends_alerts_library
Create Date: 2026-07-11 06:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016_recommendations_experiments"
down_revision = "0015_trends_alerts_library"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "brand_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("suggested_test", sa.Text(), nullable=True),
        sa.Column("learning_objective", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=48), nullable=False, server_default="rules"),
        sa.Column("category", sa.String(length=64), nullable=False, server_default="general"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("confidence between 0 and 100", name="ck_recommendations_confidence"),
        sa.CheckConstraint(
            "status in ('open', 'accepted', 'dismissed', 'converted')",
            name="ck_recommendations_status",
        ),
        sa.CheckConstraint(
            "source in ('rules', 'manual', 'llm')",
            name="ck_recommendations_source",
        ),
    )
    op.create_index(op.f("ix_recommendations_workspace_id"), "recommendations", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_recommendations_status"), "recommendations", ["status"], unique=False)

    op.create_table(
        "experiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "brand_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "linked_recommendation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recommendations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("variable", sa.String(length=160), nullable=False, server_default="hook"),
        sa.Column(
            "control_concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_concepts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "control_video_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("video_projects.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("variants", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("primary_metric", sa.String(length=32), nullable=False, server_default="roas"),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("result_metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "primary_metric in ('roas', 'cpa', 'hold_rate', 'ctr', 'custom')",
            name="ck_experiments_primary_metric",
        ),
        sa.CheckConstraint(
            "status in ('draft', 'running', 'completed', 'abandoned')",
            name="ck_experiments_status",
        ),
        sa.CheckConstraint("confidence between 0 and 100", name="ck_experiments_confidence"),
    )
    op.create_index(op.f("ix_experiments_workspace_id"), "experiments", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_experiments_status"), "experiments", ["status"], unique=False)
    op.create_index(op.f("ix_experiments_linked_recommendation_id"), "experiments", ["linked_recommendation_id"], unique=False)


def downgrade() -> None:
    op.drop_table("experiments")
    op.drop_table("recommendations")
