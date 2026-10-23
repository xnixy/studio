"""mvp3 agency operations and brand intelligence

Revision ID: 0011_mvp3_agency_brand
Revises: 0010_mvp2_completion
Create Date: 2026-07-10 22:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_mvp3_agency_brand"
down_revision = "0010_mvp2_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("contact_email", sa.String(length=256), nullable=True),
        sa.Column("contact_name", sa.String(length=120), nullable=True),
        sa.Column("logo_url", sa.String(length=1000), nullable=True),
        sa.Column("website_url", sa.String(length=1000), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("linked_workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('active', 'paused', 'archived')", name="ck_client_accounts_status"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_client_accounts_workspace_name"),
    )
    op.create_index(op.f("ix_client_accounts_workspace_id"), "client_accounts", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_client_accounts_linked_workspace_id"), "client_accounts", ["linked_workspace_id"], unique=False)

    op.create_table(
        "client_access",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="strategist"),
        sa.Column("can_approve", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("can_comment", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("can_view_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role in ('strategist', 'client', 'collaborator')", name="ck_client_access_role"),
        sa.UniqueConstraint("client_id", "user_id", name="uq_client_access_client_user"),
    )
    op.create_index(op.f("ix_client_access_client_id"), "client_access", ["client_id"], unique=False)
    op.create_index(op.f("ix_client_access_user_id"), "client_access", ["user_id"], unique=False)

    op.create_table(
        "review_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(length=48), nullable=False, server_default="custom"),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("approval_state", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("requested_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decision_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resource_type in ('concept', 'video_project', 'report', 'brief', 'custom')",
            name="ck_review_requests_resource_type",
        ),
        sa.CheckConstraint("status in ('open', 'in_review', 'closed')", name="ck_review_requests_status"),
        sa.CheckConstraint(
            "approval_state in ('pending', 'changes_requested', 'approved', 'rejected')",
            name="ck_review_requests_approval_state",
        ),
    )
    op.create_index(op.f("ix_review_requests_workspace_id"), "review_requests", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_review_requests_client_id"), "review_requests", ["client_id"], unique=False)
    op.create_index(op.f("ix_review_requests_resource_id"), "review_requests", ["resource_id"], unique=False)

    op.create_table(
        "review_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("review_request_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("review_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_review_comments_review_request_id"), "review_comments", ["review_request_id"], unique=False)
    op.create_index(op.f("ix_review_comments_workspace_id"), "review_comments", ["workspace_id"], unique=False)

    op.create_table(
        "share_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(length=48), nullable=False, server_default="custom"),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("token_prefix", sa.String(length=12), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("allow_download", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("password_hash", sa.String(length=512), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resource_type in ('concept', 'video_project', 'report', 'brief', 'custom')",
            name="ck_share_links_resource_type",
        ),
        sa.CheckConstraint("view_count >= 0", name="ck_share_links_view_count_nonnegative"),
        sa.UniqueConstraint("token_hash", name="uq_share_links_token_hash"),
    )
    op.create_index(op.f("ix_share_links_workspace_id"), "share_links", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_share_links_client_id"), "share_links", ["client_id"], unique=False)
    op.create_index(op.f("ix_share_links_resource_id"), "share_links", ["resource_id"], unique=False)
    op.create_index(op.f("ix_share_links_token_hash"), "share_links", ["token_hash"], unique=True)
    op.create_index(op.f("ix_share_links_token_prefix"), "share_links", ["token_prefix"], unique=False)

    op.create_table(
        "client_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("report_type", sa.String(length=32), nullable=False, server_default="custom"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("content", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("branding", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pdf_url", sa.String(length=1000), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("report_type in ('weekly', 'monthly', 'campaign', 'custom')", name="ck_client_reports_type"),
        sa.CheckConstraint("status in ('draft', 'published', 'archived')", name="ck_client_reports_status"),
    )
    op.create_index(op.f("ix_client_reports_workspace_id"), "client_reports", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_client_reports_client_id"), "client_reports", ["client_id"], unique=False)

    op.create_table(
        "billing_addons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addon_type", sa.String(length=48), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "addon_type in ('seats', 'monitored_competitors', 'video_credits', 'storage_gb', 'priority_rendering')",
            name="ck_billing_addons_type",
        ),
        sa.CheckConstraint("quantity > 0", name="ck_billing_addons_quantity_positive"),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_billing_addons_price_nonnegative"),
        sa.CheckConstraint("status in ('active', 'canceled')", name="ck_billing_addons_status"),
        sa.UniqueConstraint("workspace_id", "addon_type", name="uq_billing_addons_workspace_type"),
    )
    op.create_index(op.f("ix_billing_addons_workspace_id"), "billing_addons", ["workspace_id"], unique=False)

    op.create_table(
        "brand_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("client_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("voice_summary", sa.Text(), nullable=True),
        sa.Column("voice_tone", sa.String(length=120), nullable=True),
        sa.Column("voice_guidelines", sa.Text(), nullable=True),
        sa.Column("product_catalog", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("target_audiences", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("approved_claims", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("prohibited_claims", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("compliance_rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("visual_style", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("preferred_presenters", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("hooks", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("ctas", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("offers", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("seasonal_campaigns", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('draft', 'active', 'archived')", name="ck_brand_profiles_status"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_brand_profiles_workspace_name"),
    )
    op.create_index(op.f("ix_brand_profiles_workspace_id"), "brand_profiles", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_brand_profiles_client_id"), "brand_profiles", ["client_id"], unique=False)

    op.create_table(
        "brand_facts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("brand_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brand_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False, server_default="general"),
        sa.Column("fact_key", sa.String(length=160), nullable=False),
        sa.Column("fact_value", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=240), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("inferred", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("reviewed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status in ('pending', 'approved', 'rejected')", name="ck_brand_facts_status"),
        sa.CheckConstraint("confidence between 0 and 100", name="ck_brand_facts_confidence"),
    )
    op.create_index(op.f("ix_brand_facts_brand_profile_id"), "brand_facts", ["brand_profile_id"], unique=False)
    op.create_index(op.f("ix_brand_facts_workspace_id"), "brand_facts", ["workspace_id"], unique=False)

    op.create_table(
        "brand_compliance_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("brand_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resource_type", sa.String(length=48), nullable=False, server_default="custom"),
        sa.Column("resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("risk_level", sa.String(length=16), nullable=False, server_default="none"),
        sa.Column("flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("checked_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resource_type in ('concept', 'video_project', 'report', 'brief', 'custom', 'generation')",
            name="ck_brand_compliance_resource_type",
        ),
        sa.CheckConstraint("risk_level in ('none', 'low', 'medium', 'high')", name="ck_brand_compliance_risk_level"),
    )
    op.create_index(op.f("ix_brand_compliance_checks_workspace_id"), "brand_compliance_checks", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_brand_compliance_checks_brand_profile_id"), "brand_compliance_checks", ["brand_profile_id"], unique=False)
    op.create_index(op.f("ix_brand_compliance_checks_resource_id"), "brand_compliance_checks", ["resource_id"], unique=False)


def downgrade() -> None:
    op.drop_table("brand_compliance_checks")
    op.drop_table("brand_facts")
    op.drop_table("brand_profiles")
    op.drop_table("billing_addons")
    op.drop_table("client_reports")
    op.drop_table("share_links")
    op.drop_table("review_comments")
    op.drop_table("review_requests")
    op.drop_table("client_access")
    op.drop_table("client_accounts")
