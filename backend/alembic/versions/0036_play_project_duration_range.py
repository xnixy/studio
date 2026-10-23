"""Allow short Play clip durations on video_projects.

Play writes the request length (4-15s etc.) onto the shared Play project.
The old check only allowed 15/30/45/60.

Revision ID: 0036_play_duration_range
Revises: 0035_kling_video_source
"""
from alembic import op

revision = "0036_play_duration_range"
down_revision = "0035_kling_video_source"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_video_projects_target_duration", "video_projects", type_="check")
    op.create_check_constraint(
        "ck_video_projects_target_duration",
        "video_projects",
        "target_duration_seconds >= 1 AND target_duration_seconds <= 180",
    )


def downgrade() -> None:
    # Clamp any out-of-enum values before restoring the old check.
    op.execute(
        """
        UPDATE video_projects
        SET target_duration_seconds = CASE
            WHEN target_duration_seconds <= 15 THEN 15
            WHEN target_duration_seconds <= 30 THEN 30
            WHEN target_duration_seconds <= 45 THEN 45
            ELSE 60
        END
        WHERE target_duration_seconds NOT IN (15, 30, 45, 60)
        """
    )
    op.drop_constraint("ck_video_projects_target_duration", "video_projects", type_="check")
    op.create_check_constraint(
        "ck_video_projects_target_duration",
        "video_projects",
        "target_duration_seconds in (15, 30, 45, 60)",
    )
