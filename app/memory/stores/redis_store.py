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
        self._url = url
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
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
        if self._client:
            await self._client.aclose()
            logger.info("Redis connection closed")

    # ------------------------------------------------------------------ #
    # CRUD helpers
    # ------------------------------------------------------------------ #

    async def get(self, key: str) -> str | None:
        self._assert_connected()
        return await self._client.get(key)  # type: ignore[union-attr]

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self._assert_connected()
        await self._client.set(key, value, ex=ttl if ttl else None)

    async def delete(self, key: str) -> None:
        self._assert_connected()
        await self._client.delete(key)  # type: ignore[union-attr]

    async def exists(self, key: str) -> bool:
        self._assert_connected()
        return bool(await self._client.exists(key))  # type: ignore[union-attr]

    async def expire(self, key: str) -> None:
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
