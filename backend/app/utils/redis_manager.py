"""Redis connection manager for caching and state management."""
from __future__ import annotations
import json
from typing import Optional, Any
from redis.asyncio import Redis, ConnectionPool
from loguru import logger


class RedisManager:
    """Manages Redis connections and operations."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def connect(self):
        """Initialize Redis connection pool."""
        try:
            self._pool = ConnectionPool.from_url(
                self.redis_url,
                decode_responses=True,
                max_connections=50
            )
            self._client = Redis(connection_pool=self._pool)
            await self._client.ping()
            logger.info(f"Redis connected: {self.redis_url}")
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}. Continuing without cache.")
            self._client = None

    async def disconnect(self):
        """Close Redis connections."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Redis disconnected")

    @property
    def is_available(self) -> bool:
        """Check if Redis is connected."""
        return self._client is not None

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.is_available:
            return None
        try:
            value = await self._client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.debug(f"Redis get error for {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = 300):
        """Set value in cache with TTL."""
        if not self.is_available:
            return
        try:
            await self._client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.debug(f"Redis set error for {key}: {e}")

    async def delete(self, key: str):
        """Delete key from cache."""
        if not self.is_available:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.debug(f"Redis delete error for {key}: {e}")

    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        if not self.is_available:
            return
        try:
            keys = []
            async for key in self._client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await self._client.delete(*keys)
        except Exception as e:
            logger.debug(f"Redis clear pattern error for {pattern}: {e}")


# Global instance
redis_manager = RedisManager()
