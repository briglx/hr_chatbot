"""Async Redis store — thin wrapper around redis.asyncio.

All other components (SessionManager, CacheService) depend on this abstraction
rather than on the redis client directly, making it easy to swap backends in tests.
"""

from __future__ import annotations

import redis.asyncio as aioredis
import structlog

logger = structlog.get_logger(__name__)


class RedisStore:
    """Async Redis client wrapper with connect/disconnect lifecycle."""

    def __init__(self, url: str) -> None:
        """Initialize the RedisStore with the given Redis URL. The connection is not established until connect() is called."""
        self._url = url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Establish a connection to Redis. Must be called before using the store."""
        self._client = aioredis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        await self._client.ping()
        logger.info("Redis connection established", url=self._url)

    async def disconnect(self) -> None:
        """Close the Redis connection. Should be called during application shutdown to clean up resources."""
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")

    # ------------------------------------------------------------------ #
    # CRUD helpers
    # ------------------------------------------------------------------ #

    async def get(self, key: str) -> str | None:
        """Get the value of a key from Redis. Returns None if the key does not exist."""
        self._assert_connected()
        return await self._client.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Set the value of a key in Redis with an optional TTL (in seconds). If ttl is None, the key will not expire."""
        self._assert_connected()
        await self._client.set(key, value, ex=ttl if ttl else None)

    async def delete(self, key: str) -> None:
        """Delete a key from Redis. Does nothing if the key does not exist."""
        self._assert_connected()
        await self._client.delete(key)  # type: ignore[union-attr]

    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis. Returns True if the key exists, False otherwise."""
        self._assert_connected()
        return bool(await self._client.exists(key))  # type: ignore[union-attr]

    async def expire(self, key: str) -> None:
        """Remove the TTL from a key, making it persistent. Does nothing if the key does not exist or is already persistent."""
        self._assert_connected()
        await self._client.expire(key)  # type: ignore[union-attr]

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _assert_connected(self) -> None:
        if self._client is None:
            raise RuntimeError(
                "RedisStore is not connected. Call connect() before use."
            )
