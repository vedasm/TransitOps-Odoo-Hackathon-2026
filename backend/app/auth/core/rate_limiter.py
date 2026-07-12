from typing import Optional
import redis.asyncio as redis

class RateLimiter:
    def __init__(self, redis_client: redis.Redis) -> None:
        self.redis = redis_client

    def _key(self, identifier: str, action: str) -> str:
        return f"rate_limit:{identifier}:{action}"

    async def check_rate_limit(
        self,
        identifier: str,
        action: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        key = self._key(identifier, action)
        count = await self.redis.get(key)
        if count is None:
            return True
        return int(count) < limit

    async def increment_counter(
        self,
        identifier: str,
        action: str,
        window_seconds: int,
    ) -> int:
        key = self._key(identifier, action)
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()

        if ttl in (-1, -2):
            await self.redis.expire(key, window_seconds)

        return int(count)

    async def get_remaining(
        self,
        identifier: str,
        action: str,
        limit: int,
    ) -> int:
        key = self._key(identifier, action)
        count = await self.redis.get(key)
        if count is None:
            return limit
        remaining = limit - int(count)
        return remaining if remaining > 0 else 0