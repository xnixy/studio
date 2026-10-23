"""Drop ads OS tables (monitoring, performance, optimize, research, agency clients)

Revision ID: 0026_drop_ads_os
Revises: 0025_image_ads
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_drop_ads_os"
down_revision = "0025_image_ads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Drop FKs from keep-tables onto client_accounts before dropping agency graph
    for table, col, fk_hint in (
        ("library_items", "client_id", "%client_accounts%"),
        ("brand_profiles", "client_id", "%client_accounts%"),
        ("image_packs", "client_id", "%client_accounts%"),
    ):
        # Use CAST(... AS regclass), not :table::regclass — SQLAlchemy bind
        # params clash with Postgres :: cast syntax and leave :table unbound.
        rows = conn.execute(
            sa.text(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = CAST(:table AS regclass)
                  AND contype = 'f'
                  AND pg_get_constraintdef(oid) ILIKE :hint
                """
            ),
            {"table": table, "hint": f"%{col}%"},
        ).fetchall()
        for (conname,) in rows:
            op.drop_constraint(conname, table, type_="foreignkey")

    # Child → parent drop order
    tables = [
        "competitor_ad_sightings",
        "competitor_ads",
        "landing_page_snapshots",
        "monitored_competitors",
        "performance_metrics",
        "performance_imports",
        "experiments",
        "recommendations",
        "alert_events",
        "alert_subscriptions",
        "trend_entities",
        "competitor_observations",
        "competitors",
        "trend_reports",
        "trend_watchlists",
        "review_comments",
        "review_requests",
        "client_reports",
        "client_access_invitations",
        "client_access",
        "client_accounts",
    ]
    for name in tables:
        op.execute(sa.text(f'DROP TABLE IF EXISTS "{name}" CASCADE'))

    # Optional: clear ads job rows
    op.execute(
        sa.text(
            """
            DELETE FROM background_jobs
            WHERE job_type IN (
                'monitoring.scan',
                'performance.import',
                'recommendation.run',
                'trend.score',
                'alert.digest'
            )
            """
        )
    )


def downgrade() -> None:
    # Ads OS tables are not recreated; restore from backup if needed.
    pass
