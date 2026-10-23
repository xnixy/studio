"""Expo rejects a whole batch that spans experience ids.

One user holding a store-build token next to a dev-client token took down every
push for that user, forever — the bad token was never pruned, so every later send
hit the same wall. These cover the split and the cleanup that ends it.
"""
import asyncio

import httpx
import pytest

from app import push as push_module
from app.push import send_expo_push_to_user

USER_ID = "00000000-0000-0000-0000-0000000000aa"
STORE = "ExponentPushToken[store-build]"
DEV = "ExponentPushToken[dev-client]"


class _Response:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self) -> object:
        if self._payload is None:
            raise ValueError("no body")
        return self._payload


def _conflict(groups: dict[str, list[str]] | None) -> dict:
    err: dict = {"code": "PUSH_TOO_MANY_EXPERIENCE_IDS", "message": "conflicting tokens"}
    if groups is not None:
        err["details"] = groups
    return {"errors": [err]}


def _ok(tickets: list[dict]) -> dict:
    return {"data": tickets}


class _Session:
    """Token lookup only. Cleanup deliberately runs on its own session."""

    def __init__(self, tokens: list[str]) -> None:
        self.tokens = tokens

    async def scalars(self, _query: object):
        tokens = self.tokens

        class _Result:
            def all(self) -> list[str]:
                return tokens

        return _Result()


def _install(monkeypatch: pytest.MonkeyPatch, responses: list[_Response]) -> list[list[str]]:
    """Fake Expo. Returns the list of token batches actually posted."""
    posted: list[list[str]] = []
    queue = list(responses)

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, _url, json=None):
            posted.append([m["to"] for m in json])
            return queue.pop(0) if queue else _Response(200, _ok([{"status": "ok"} for _ in json]))

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    return posted


def _forget_spy(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Capture cleanup targets without touching a database."""
    dropped: list[str] = []

    async def _fake_forget(tokens: list[str]) -> None:
        dropped.extend(tokens)

    monkeypatch.setattr(push_module, "_forget_tokens", _fake_forget)
    return dropped


def _send(tokens: list[str]) -> None:
    asyncio.run(
        send_expo_push_to_user(
            _Session(tokens), user_id=USER_ID, title="Your clip is ready", body="Tap to watch"
        )
    )


def test_single_experience_batch_stays_one_request(monkeypatch: pytest.MonkeyPatch) -> None:
    posted = _install(monkeypatch, [_Response(200, _ok([{"status": "ok"}, {"status": "ok"}]))])
    _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert posted == [[STORE, DEV]]


def test_conflict_splits_into_one_request_per_experience(monkeypatch: pytest.MonkeyPatch) -> None:
    posted = _install(
        monkeypatch,
        [
            _Response(400, _conflict({"@studio/studio-ios": [STORE], "@anonymous/studio": [DEV]})),
            _Response(200, _ok([{"status": "ok"}])),
            _Response(200, _ok([{"status": "ok"}])),
        ],
    )
    _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert posted[0] == [STORE, DEV]
    retries = sorted(posted[1:])
    assert retries == [[DEV], [STORE]]
    # Every token delivered exactly once across the retries.
    assert sorted(t for batch in posted[1:] for t in batch) == sorted([DEV, STORE])


def test_conflict_without_usable_details_falls_back_to_one_per_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    posted = _install(
        monkeypatch,
        [
            _Response(400, _conflict(None)),
            _Response(200, _ok([{"status": "ok"}])),
            _Response(200, _ok([{"status": "ok"}])),
        ],
    )
    _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert posted[1:] == [[STORE], [DEV]]


def test_token_missing_from_details_still_gets_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    orphan = "ExponentPushToken[unattributed]"
    posted = _install(
        monkeypatch,
        [_Response(400, _conflict({"@studio/studio-ios": [STORE], "@anonymous/studio": [DEV]}))],
    )
    _forget_spy(monkeypatch)

    _send([STORE, DEV, orphan])

    assert [orphan] in posted[1:]


def test_split_happens_at_most_once(monkeypatch: pytest.MonkeyPatch) -> None:
    # A group that still conflicts must land in the logs, not start a retry loop.
    posted = _install(
        monkeypatch,
        [
            _Response(400, _conflict({"@studio/studio-ios": [STORE], "@anonymous/studio": [DEV]})),
            _Response(400, _conflict({"@studio/studio-ios": [STORE]})),
            _Response(400, _conflict({"@anonymous/studio": [DEV]})),
        ],
    )
    _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert len(posted) == 3


def test_other_400_is_not_resent(monkeypatch: pytest.MonkeyPatch) -> None:
    posted = _install(
        monkeypatch, [_Response(400, {"errors": [{"code": "PUSH_TOO_MANY_NOTIFICATIONS"}]})]
    )
    _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert len(posted) == 1


def test_unregistered_device_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        [
            _Response(
                200,
                _ok(
                    [
                        {"status": "ok"},
                        {"status": "error", "details": {"error": "DeviceNotRegistered"}},
                    ]
                ),
            )
        ],
    )
    dropped = _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert dropped == [DEV]


def test_healthy_tickets_drop_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(monkeypatch, [_Response(200, _ok([{"status": "ok"}, {"status": "ok"}]))])
    dropped = _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert dropped == []


def test_dead_token_found_after_a_split_is_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    _install(
        monkeypatch,
        [
            _Response(400, _conflict({"@studio/studio-ios": [STORE], "@anonymous/studio": [DEV]})),
            _Response(200, _ok([{"status": "ok"}])),
            _Response(200, _ok([{"status": "error", "details": {"error": "DeviceNotRegistered"}}])),
        ],
    )
    dropped = _forget_spy(monkeypatch)

    _send([STORE, DEV])

    assert dropped == [DEV]


def test_transport_failure_never_reaches_the_caller(monkeypatch: pytest.MonkeyPatch) -> None:
    class ExplodingClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, _url, json=None):
            raise httpx.ConnectError("expo unreachable")

    monkeypatch.setattr(httpx, "AsyncClient", ExplodingClient)
    _forget_spy(monkeypatch)

    _send([STORE])  # must not raise


def test_no_tokens_means_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    posted = _install(monkeypatch, [])
    _forget_spy(monkeypatch)

    _send([])

    assert posted == []
