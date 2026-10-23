"""credit pack grants + expanded recurring addon types

Revision ID: 0021_credit_packs
Revises: 0020_creator_plans_media_meters
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0021_credit_packs"
down_revision = "0020_creator_plans_media_meters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_billing_addons_type", "billing_addons", type_="check")
    op.create_check_constraint(
        "ck_billing_addons_type",
        "billing_addons",
        "addon_type in ('seats', 'monitored_competitors', 'video_credits', 'image_generations', "
        "'avatar_lipsyncs', 'script_generations', 'voiceover_minutes', 'storage_gb', 'priority_rendering')",
    )

    op.create_table(
        "billing_credit_grants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("pack_name", sa.String(length=48), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("grants", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("stripe_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("purchased_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("amount_cents >= 0", name="ck_billing_credit_grants_amount_nonnegative"),
        sa.CheckConstraint("status in ('active', 'refunded', 'expired')", name="ck_billing_credit_grants_status"),
        sa.UniqueConstraint("stripe_checkout_session_id", name="uq_billing_credit_grants_stripe_session"),
    )
    op.create_index("ix_billing_credit_grants_workspace_id", "billing_credit_grants", ["workspace_id"])


def downgrade() -> None:
    op.drop_index("ix_billing_credit_grants_workspace_id", table_name="billing_credit_grants")
    op.drop_table("billing_credit_grants")

    op.drop_constraint("ck_billing_addons_type", "billing_addons", type_="check")
    op.create_check_constraint(
        "ck_billing_addons_type",
        "billing_addons",
        "addon_type in ('seats', 'monitored_competitors', 'video_credits', 'image_generations', "
        "'avatar_lipsyncs', 'storage_gb', 'priority_rendering')",
    )
