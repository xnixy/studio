"""creator plans + separate media meters (image / video / avatar lipsync)

Revision ID: 0020_creator_plans_media_meters
Revises: 0019_admin_limit_controls
"""
from alembic import op

revision = "0020_creator_plans_media_meters"
down_revision = "0019_admin_limit_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.create_check_constraint(
        "ck_subscriptions_plan",
        "subscriptions",
        "plan in ('free', 'creator', 'creator_pro', 'starter', 'pro', 'agency')",
    )

    op.drop_constraint("ck_billing_addons_type", "billing_addons", type_="check")
    op.create_check_constraint(
        "ck_billing_addons_type",
        "billing_addons",
        "addon_type in ('seats', 'monitored_competitors', 'video_credits', 'image_generations', 'avatar_lipsyncs', 'storage_gb', 'priority_rendering')",
    )


def downgrade() -> None:
    # Downgrade only if no workspaces use creator plans / new add-on types.
    op.drop_constraint("ck_billing_addons_type", "billing_addons", type_="check")
    op.create_check_constraint(
        "ck_billing_addons_type",
        "billing_addons",
        "addon_type in ('seats', 'monitored_competitors', 'video_credits', 'storage_gb', 'priority_rendering')",
    )

    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.create_check_constraint(
        "ck_subscriptions_plan",
        "subscriptions",
        "plan in ('free', 'starter', 'pro', 'agency')",
    )
