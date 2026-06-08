"""Cache service — Redis with in-memory fallback."""

import json
from typing import Any, Optional


class CacheService:
    """Unified cache with Redis primary and in-memory fallback."""

    def __init__(self, redis_url: Optional[str] = None):
        self._redis = None
        self._memory: dict = {}
        self._redis_url = redis_url
        if redis_url:
            self._init_redis()

    def _init_redis(self):
        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        except Exception:
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        if self._redis:
            val = await self._redis.get(key)
            return json.loads(val) if val else None
        return self._memory.get(key)

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if self._redis:
            await self._redis.setex(key, ttl, json.dumps(value))
        else:
            self._memory[key] = value

    async def delete(self, key: str) -> None:
        if self._redis:
            await self._redis.delete(key)
        else:
            self._memory.pop(key, None)

    async def flush(self) -> None:
        if self._redis:
            await self._redis.flushdb()
        else:
            self._memory.clear()