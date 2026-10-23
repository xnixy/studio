"""Simplify plans to free + starter + creator + studio.

Revision ID: 0029_simplify_plans
Revises: 0028_iap_transactions
"""
from alembic import op

revision = "0029_simplify_plans"
down_revision = "0028_iap_transactions"
branch_labels = None
depends_on = None

# One-time data remap. Old names are not kept in app code after this migration.
_PLAN_REMAP = """
UPDATE subscriptions SET plan = CASE plan
    WHEN 'image' THEN 'starter'
    WHEN 'image_pro' THEN 'creator'
    WHEN 'creator_pro' THEN 'creator'
    WHEN 'pro' THEN 'studio'
    WHEN 'agency' THEN 'studio'
    ELSE plan
END
WHERE plan IN ('image', 'image_pro', 'creator_pro', 'pro', 'agency')
"""


def upgrade() -> None:
    op.execute(_PLAN_REMAP)
    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.create_check_constraint(
        "ck_subscriptions_plan",
        "subscriptions",
        "plan in ('free', 'starter', 'creator', 'studio')",
    )


def downgrade() -> None:
    # Downgrade only if no workspaces use studio (new top tier name).
    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.create_check_constraint(
        "ck_subscriptions_plan",
        "subscriptions",
        "plan in ('free', 'creator', 'creator_pro', 'image', 'image_pro', 'starter', 'pro', 'agency')",
    )
