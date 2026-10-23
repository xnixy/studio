from __future__ import annotations

import time
from dataclasses import dataclass, field

from redis.asyncio import Redis


@dataclass
class MemoryBucket:
    count: int
    expires_at: float


@dataclass
class MemoryValue:
    value: str
    expires_at: float


@dataclass
class RateLimiter:
    redis_url: str | None
    redis: Redis | None = None
    memory: dict[str, MemoryBucket] = field(default_factory=dict)
    memory_values: dict[str, MemoryValue] = field(default_factory=dict)

    async def connect(self) -> None:
        if not self.redis_url:
            return
        self.redis = Redis.from_url(self.redis_url, encoding="utf-8", decode_responses=True)
        try:
            await self.redis.ping()
        except Exception:
            await self.close()

    async def close(self) -> None:
        if self.redis is None:
            return
        client = self.redis
        self.redis = None
        try:
            await client.aclose(close_connection_pool=True)
        except Exception:
            try:
                await client.connection_pool.disconnect(inuse_connections=True)
            except Exception:
                pass

    @property
    def using_redis(self) -> bool:
        return self.redis is not None

    async def hit(
        self,
        key: str,
        limit: int,
        window_seconds: int,
        *,
        require_redis: bool = False,
    ) -> bool:
        """Return True if under limit. Redis path is atomic (INCR + EXPIRE on first hit).

        When *require_redis* is True and Redis is unavailable, return False (fail closed)
        so auth-sensitive routes cannot be brute-forced across multi-instance memory buckets.
        """
        if self.redis is not None:
            try:
                # Pipeline keeps incr+expire close together so a crash is less likely to leave
                # a key without TTL. expire is only needed when the key is first created.
                pipe = self.redis.pipeline()
                pipe.incr(key)
                pipe.ttl(key)
                results = await pipe.execute()
                count = int(results[0])
                ttl = int(results[1])
                if ttl < 0:
                    # -1 = no expiry, -2 = missing (shouldn't happen after incr)
                    await self.redis.expire(key, window_seconds)
                return count <= limit
            except Exception:
                await self.close()
                if require_redis:
                    return False

        if require_redis:
            return False

        now = time.monotonic()
        bucket = self.memory.get(key)
        if bucket is None or bucket.expires_at <= now:
            self.memory[key] = MemoryBucket(count=1, expires_at=now + window_seconds)
            return True

        bucket.count += 1
        return bucket.count <= limit

    async def get(self, key: str) -> str | None:
        """Read a string value (Redis preferred; process-local memory fallback)."""
        if self.redis is not None:
            try:
                value = await self.redis.get(key)
                return str(value) if value is not None else None
            except Exception:
                await self.close()

        now = time.monotonic()
        entry = self.memory_values.get(key)
        if entry is None or entry.expires_at <= now:
            if entry is not None:
                self.memory_values.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Write a string value with TTL (Redis preferred; process-local memory fallback)."""
        ttl = max(1, int(ttl_seconds))
        if self.redis is not None:
            try:
                await self.redis.set(key, value, ex=ttl)
                return
            except Exception:
                await self.close()

        self.memory_values[key] = MemoryValue(value=value, expires_at=time.monotonic() + ttl)

    async def set_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        """Atomic SETNX with TTL. True when this call claimed the key.

        Redis path is atomic; the memory fallback is per-process only, same
        caveat as every other limiter path.
        """
        ttl = max(1, int(ttl_seconds))
        if self.redis is not None:
            try:
                claimed = await self.redis.set(key, value, ex=ttl, nx=True)
                return bool(claimed)
            except Exception:
                await self.close()

        now = time.monotonic()
        entry = self.memory_values.get(key)
        if entry is not None and entry.expires_at > now:
            return False
        self.memory_values[key] = MemoryValue(value=value, expires_at=now + ttl)
        return True

    async def delete(self, key: str) -> None:
        """Best-effort delete (Redis preferred; process-local memory fallback)."""
        if self.redis is not None:
            try:
                await self.redis.delete(key)
                return
            except Exception:
                await self.close()

        self.memory_values.pop(key, None)
