"""Delete Library talking and lip-sync clips that used retired xAI stock voices.

Revision ID: 0043_purge_xai_stock_clips
Revises: 0042_voices_elevenlabs
"""
from alembic import op

revision = "0043_purge_xai_stock_clips"
down_revision = "0042_voices_elevenlabs"
branch_labels = None
depends_on = None

# Keep in sync with app.stock_voices.LEGACY_XAI_VOICE_IDS.
_LEGACY = (
    "ara",
    "eve",
    "leo",
    "rex",
    "sal",
    "altair",
    "atlas",
    "carina",
    "castor",
    "celeste",
    "cosmo",
    "helios",
    "helix",
    "iris",
    "kepler",
    "lumen",
    "luna",
    "lux",
    "naksh",
    "orion",
    "perseus",
    "rigel",
    "sirius",
    "ursa",
    "zagan",
    "zenith",
    "wellness",
    "support",
    "male",
    "female",
)


def upgrade() -> None:
    ids = ", ".join(f"'{name}'" for name in _LEGACY)
    # Videos only. Faces are play_mode=avatar with no voice; the first cut of
    # this migration deleted them. restore_purged_faces.py puts those rows back.
    op.execute(
        f"""
        DELETE FROM video_assets
        WHERE asset_type = 'video'
          AND coalesce(metadata->>'play_mode', '') IN ('avatar', 'lipsync')
          AND coalesce(metadata->>'mode', '') IS DISTINCT FROM 'avatar_source_image'
          AND coalesce(metadata->>'face_library', '') NOT IN ('true', 'True')
          AND (
            lower(coalesce(metadata->>'voice', '')) IN ({ids})
            OR (
              coalesce(metadata->>'play_mode', '') = 'avatar'
              AND coalesce(trim(metadata->>'voice'), '') = ''
            )
          )
        """
    )


def downgrade() -> None:
    # Deleted clips cannot be restored.
    pass
