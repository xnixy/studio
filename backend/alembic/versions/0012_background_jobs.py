"""mvp3 background jobs spine

Revision ID: 0012_background_jobs
Revises: 0011_mvp3_agency_brand
Create Date: 2026-07-10 23:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0012_background_jobs"
down_revision = "0011_mvp3_agency_brand"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("job_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column(
            "usage_event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usage_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("cancel_requested", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status in ('queued', 'running', 'waiting_for_provider', 'completed', 'failed', 'canceled')",
            name="ck_background_jobs_status",
        ),
        sa.CheckConstraint("attempts >= 0", name="ck_background_jobs_attempts_nonnegative"),
        sa.CheckConstraint("max_attempts >= 1", name="ck_background_jobs_max_attempts_positive"),
        sa.CheckConstraint("priority >= 0", name="ck_background_jobs_priority_nonnegative"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_background_jobs_workspace_idempotency"),
    )
    op.create_index(op.f("ix_background_jobs_workspace_id"), "background_jobs", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_background_jobs_job_type"), "background_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_background_jobs_status"), "background_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_background_jobs_scheduled_for"), "background_jobs", ["scheduled_for"], unique=False)
    op.create_index(
        "ix_background_jobs_claim_queue",
        "background_jobs",
        ["status", "scheduled_for", "priority", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_background_jobs_claim_queue", table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_scheduled_for"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_status"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_job_type"), table_name="background_jobs")
    op.drop_index(op.f("ix_background_jobs_workspace_id"), table_name="background_jobs")
    op.drop_table("background_jobs")
