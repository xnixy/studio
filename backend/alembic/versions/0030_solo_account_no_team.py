"""Solo accounts: drop team invites, collapse workspace types.

Revision ID: 0030_solo_account
Revises: 0029_simplify_plans
"""
from alembic import op

revision = "0030_solo_account"
down_revision = "0029_simplify_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop team invitation table (product no longer supports workspace invites).
    op.execute("DROP TABLE IF EXISTS workspace_invitations CASCADE")

    # Drop type check first so we can rewrite values.
    op.drop_constraint("ck_workspaces_type", "workspaces", type_="check")
    op.execute("UPDATE workspaces SET type = 'personal'")
    op.create_check_constraint(
        "ck_workspaces_type",
        "workspaces",
        "type in ('personal', 'brand')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_workspaces_type", "workspaces", type_="check")
    op.execute("UPDATE workspaces SET type = 'brand' WHERE type = 'personal'")
    op.create_check_constraint(
        "ck_workspaces_type",
        "workspaces",
        "type in ('brand', 'agency')",
    )
