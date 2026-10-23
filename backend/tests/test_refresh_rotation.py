"""A replayed refresh token must not sign the account out everywhere.

Revoking every session for the user meant one phone holding a token whose
refresh response was dropped took the website's session down with it.
"""
import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.routers.auth import REFRESH_ROTATION_GRACE_SECONDS
from app.routers.auth_session import is_rotation_race, revoke_refresh_family


class _Stored:
    def __init__(self, *, revoked_at, family_id=None, user_id=None) -> None:
        self.revoked_at = revoked_at
        self.family_id = family_id
        self.user_id = user_id or uuid.uuid4()


class _Session:
    """Captures the statement so we can assert what the WHERE clause targets."""

    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement) -> None:
        self.statements.append(
            str(statement.compile(compile_kwargs={"literal_binds": False}))
        )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_just_rotated_token_is_a_race() -> None:
    stored = _Stored(revoked_at=_now() - timedelta(seconds=5))
    assert is_rotation_race(stored, _now(), REFRESH_ROTATION_GRACE_SECONDS) is True


def test_long_rotated_token_is_not_a_race() -> None:
    stored = _Stored(revoked_at=_now() - timedelta(hours=6))
    assert is_rotation_race(stored, _now(), REFRESH_ROTATION_GRACE_SECONDS) is False


def test_live_token_is_not_a_race() -> None:
    assert is_rotation_race(_Stored(revoked_at=None), _now(), REFRESH_ROTATION_GRACE_SECONDS) is False


def test_replay_revokes_the_chain_not_the_account() -> None:
    session = _Session()
    stored = _Stored(revoked_at=_now() - timedelta(hours=6), family_id=uuid.uuid4())

    asyncio.run(revoke_refresh_family(session, stored, _now()))

    assert len(session.statements) == 1
    sql = session.statements[0]
    assert "family_id" in sql
    # The whole point: other sign-ins for this user stay alive.
    assert "user_id" not in sql


def test_legacy_row_without_a_chain_revokes_nothing_extra() -> None:
    session = _Session()
    stored = _Stored(revoked_at=_now() - timedelta(hours=6), family_id=None)

    asyncio.run(revoke_refresh_family(session, stored, _now()))

    assert session.statements == []
