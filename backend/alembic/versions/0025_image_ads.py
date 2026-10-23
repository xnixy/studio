"""image ad packs and creatives

Revision ID: 0025_image_ads
Revises: 0024_notifications
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0025_image_ads"
down_revision = "0024_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ad_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "ad_concept_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ad_concepts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "brand_profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "brand_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("client_accounts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=180), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("placements", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("brand_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column(
            "created_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status in ('draft', 'generating', 'ready', 'partial', 'failed')",
            name="ck_image_packs_status",
        ),
    )
    op.create_index("ix_image_packs_workspace_id", "image_packs", ["workspace_id"])
    op.create_index("ix_image_packs_ad_project_id", "image_packs", ["ad_project_id"])
    op.create_index("ix_image_packs_ad_concept_id", "image_packs", ["ad_concept_id"])
    op.create_index("ix_image_packs_brand_profile_id", "image_packs", ["brand_profile_id"])
    op.create_index("ix_image_packs_brand_template_id", "image_packs", ["brand_template_id"])
    op.create_index("ix_image_packs_client_id", "image_packs", ["client_id"])

    op.create_table(
        "image_creatives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "pack_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("image_packs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("variant_label", sa.String(length=120), nullable=False, server_default="primary"),
        sa.Column("hook_text", sa.Text(), nullable=True),
        sa.Column("headline", sa.String(length=240), nullable=True),
        sa.Column("cta_text", sa.String(length=160), nullable=True),
        sa.Column("body_copy", sa.Text(), nullable=True),
        sa.Column("placement_key", sa.String(length=64), nullable=False, server_default="meta_feed_1x1"),
        sa.Column("platform", sa.String(length=32), nullable=False, server_default="meta_feed"),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False, server_default="1:1"),
        sa.Column("width", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("height", sa.Integer(), nullable=False, server_default="1080"),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_model", sa.String(length=120), nullable=True),
        sa.Column("provider_url", sa.String(length=1000), nullable=True),
        sa.Column("storage_url", sa.String(length=1000), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("overlay_spec", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("cost_usd_ticks", sa.Integer(), nullable=True),
        sa.Column("compliance_risk", sa.String(length=16), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "status in ('pending', 'processing', 'ready', 'failed')",
            name="ck_image_creatives_status",
        ),
        sa.CheckConstraint(
            "aspect_ratio in ('1:1', '4:5', '9:16', '1.91:1')",
            name="ck_image_creatives_aspect_ratio",
        ),
        sa.CheckConstraint(
            "compliance_risk is null or compliance_risk in ('none', 'low', 'medium', 'high')",
            name="ck_image_creatives_compliance_risk",
        ),
    )
    op.create_index("ix_image_creatives_pack_id", "image_creatives", ["pack_id"])
    op.create_index("ix_image_creatives_workspace_id", "image_creatives", ["workspace_id"])

    # Expand compliance resource types for image ads.
    op.drop_constraint("ck_brand_compliance_resource_type", "brand_compliance_checks", type_="check")
    op.create_check_constraint(
        "ck_brand_compliance_resource_type",
        "brand_compliance_checks",
        "resource_type in ('concept', 'video_project', 'report', 'brief', 'custom', 'generation', 'image_pack', 'image_creative')",
    )

    # Image-first plan SKUs
    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.create_check_constraint(
        "ck_subscriptions_plan",
        "subscriptions",
        "plan in ('free', 'creator', 'creator_pro', 'image', 'image_pro', 'starter', 'pro', 'agency')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_subscriptions_plan", "subscriptions", type_="check")
    op.create_check_constraint(
        "ck_subscriptions_plan",
        "subscriptions",
        "plan in ('free', 'creator', 'creator_pro', 'starter', 'pro', 'agency')",
    )
    op.drop_constraint("ck_brand_compliance_resource_type", "brand_compliance_checks", type_="check")
    op.create_check_constraint(
        "ck_brand_compliance_resource_type",
        "brand_compliance_checks",
        "resource_type in ('concept', 'video_project', 'report', 'brief', 'custom', 'generation')",
    )
    op.drop_table("image_creatives")
    op.drop_table("image_packs")
