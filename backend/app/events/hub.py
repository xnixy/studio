"""Redis-backed (with in-process fallback) pub/sub for workspace live events."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "studio:ws:workspace:"
PRESENCE_KEY_PREFIX = "studio:presence:workspace:"
PRESENCE_TTL_SECONDS = 45


class EventHub:
    """Fan-out live events to WebSocket subscribers.

    When Redis is available, publish goes to Redis and every API process
    receives via PSUBSCRIBE (including the publisher). When Redis is down,
    local in-process queues still work for single-process dev.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()
        self._redis: Redis | None = None
        self._pubsub: Any = None
        self._listener_task: asyncio.Task[None] | None = None
        self._process_id = str(uuid.uuid4())

    @property
    def redis_connected(self) -> bool:
        return self._redis is not None

    async def ensure_publisher(self, redis_url: str | None = None) -> None:
        """Connect Redis for publish-only (workers). Safe to call repeatedly."""
        if self._redis is not None:
            return
        url = redis_url
        if not url:
            try:
                from app.config import get_settings

                url = get_settings().redis_url
            except Exception:
                url = None
        if not url:
            return
        try:
            client = Redis.from_url(url, encoding="utf-8", decode_responses=True)
            await client.ping()
            self._redis = client
        except Exception as exc:
            logger.debug("event hub publisher connect failed: %s", exc)

    async def start(self, redis_url: str | None) -> None:
        if not redis_url:
            logger.info("event hub: no REDIS_URL; using in-process fan-out only")
            return
        try:
            self._redis = Redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            await self._redis.ping()
            self._pubsub = self._redis.pubsub()
            await self._pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
            self._listener_task = asyncio.create_task(self._listen_redis(), name="event-hub-redis")
            logger.info("event hub: Redis pub/sub started")
        except Exception as exc:
            logger.warning("event hub: Redis unavailable (%s); in-process only", exc)
            await self._close_redis_only()

    async def stop(self) -> None:
        """Tear down listener + Redis while the event loop is still running.

        Avoids redis.asyncio AbstractConnection.__del__ raising
        \"Event loop is closed\" during uvicorn --reload shutdown.
        """
        if self._listener_task is not None:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.debug("event hub listener stop error", exc_info=True)
            self._listener_task = None
        # Drop in-process queues so GC does not retain redis-backed state.
        async with self._lock:
            self._subscribers.clear()
        self._local_presence.clear()
        await self._close_redis_only()

    async def _close_redis_only(self) -> None:
        if self._pubsub is not None:
            try:
                await self._pubsub.punsubscribe()
            except Exception:
                logger.debug("event hub pubsub unsubscribe failed", exc_info=True)
            try:
                await self._pubsub.aclose()
            except Exception:
                logger.debug("event hub pubsub aclose failed", exc_info=True)
            self._pubsub = None
        if self._redis is not None:
            client = self._redis
            self._redis = None
            try:
                # close_connection_pool=True disconnects idle+in-use connections
                # before the loop is torn down on process reload.
                await client.aclose(close_connection_pool=True)
            except Exception:
                try:
                    await client.connection_pool.disconnect(inuse_connections=True)
                except Exception:
                    logger.debug("event hub redis disconnect failed", exc_info=True)

    async def subscribe(self, workspace_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=128)
        async with self._lock:
            self._subscribers.setdefault(workspace_id, set()).add(queue)
        return queue

    async def unsubscribe(self, workspace_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            buckets = self._subscribers.get(workspace_id)
            if not buckets:
                return
            buckets.discard(queue)
            if not buckets:
                self._subscribers.pop(workspace_id, None)

    async def publish(self, event: dict[str, Any]) -> None:
        workspace_id = str(event.get("workspace_id") or "")
        if not workspace_id:
            return
        if self._redis is None:
            await self.ensure_publisher()
        envelope = {**event, "_origin": self._process_id}
        if self._redis is not None:
            try:
                channel = f"{CHANNEL_PREFIX}{workspace_id}"
                await self._redis.publish(channel, json.dumps(envelope, default=str))
                return
            except Exception as exc:
                logger.warning("event hub redis publish failed: %s", exc)
                await self._close_redis_only()
        await self._local_publish(workspace_id, event)

    async def _local_publish(self, workspace_id: str, event: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._subscribers.get(workspace_id, ()))
        for queue in targets:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    _ = queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass

    async def _listen_redis(self) -> None:
        assert self._pubsub is not None
        try:
            while True:
                message = await self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    await asyncio.sleep(0.01)
                    continue
                if message.get("type") not in {"pmessage", "message"}:
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                # Deliver to local subscribers (including events we published).
                workspace_id = str(event.get("workspace_id") or "")
                if not workspace_id:
                    channel = message.get("channel") or message.get("pattern") or ""
                    if isinstance(channel, str) and channel.startswith(CHANNEL_PREFIX):
                        workspace_id = channel[len(CHANNEL_PREFIX) :]
                clean = {k: v for k, v in event.items() if k != "_origin"}
                if workspace_id:
                    await self._local_publish(workspace_id, clean)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("event hub redis listener crashed")

    # --- presence (Redis when available; otherwise process-local) ---

    _local_presence: dict[str, dict[str, dict[str, Any]]] = {}

    async def presence_touch(
        self,
        workspace_id: str,
        user_id: str,
        *,
        display_name: str | None = None,
        path: str | None = None,
    ) -> None:
        payload = {
            "user_id": user_id,
            "display_name": display_name or "",
            "path": path or "",
            "last_seen": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        if self._redis is not None:
            try:
                key = f"{PRESENCE_KEY_PREFIX}{workspace_id}"
                await self._redis.hset(key, user_id, json.dumps(payload))
                await self._redis.expire(key, PRESENCE_TTL_SECONDS)
                return
            except Exception as exc:
                logger.debug("presence redis failed: %s", exc)
        self._local_presence.setdefault(workspace_id, {})[user_id] = payload

    async def presence_leave(self, workspace_id: str, user_id: str) -> None:
        if self._redis is not None:
            try:
                await self._redis.hdel(f"{PRESENCE_KEY_PREFIX}{workspace_id}", user_id)
            except Exception:
                pass
        bucket = self._local_presence.get(workspace_id)
        if bucket is not None:
            bucket.pop(user_id, None)

    async def presence_snapshot(self, workspace_id: str) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        if self._redis is not None:
            try:
                raw = await self._redis.hgetall(f"{PRESENCE_KEY_PREFIX}{workspace_id}")
                for value in raw.values():
                    try:
                        members.append(json.loads(value))
                    except json.JSONDecodeError:
                        continue
                return members
            except Exception:
                pass
        return list(self._local_presence.get(workspace_id, {}).values())


event_hub = EventHub()
