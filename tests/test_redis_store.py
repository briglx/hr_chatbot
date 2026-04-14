from unittest.mock import AsyncMock, patch

import pytest

from app.memory.stores.redis_store import RedisStore

# -----------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------


class TestRedisStore:
    @pytest.fixture
    def mock_redis_client(self):
        """A mock redis.asyncio client."""
        client = AsyncMock()
        client.ping = AsyncMock()
        client.get = AsyncMock(return_value=None)
        client.set = AsyncMock()
        client.setex = AsyncMock()
        client.delete = AsyncMock()
        client.exists = AsyncMock(return_value=0)
        client.expire = AsyncMock()
        client.aclose = AsyncMock()
        return client

    @pytest.fixture
    def store(self, mock_redis_client) -> RedisStore:
        """A connected RedisStore with a mocked client."""
        with patch(
            "app.memory.stores.redis_store.aioredis.from_url",
            return_value=mock_redis_client,
        ):
            store = RedisStore("redis://localhost:6379/0")
            store._client = mock_redis_client
            return store

    # -----------------------------------------------------------------------
    # connect()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_connect_calls_ping(self, mock_redis_client):
        with patch(
            "app.memory.stores.redis_store.aioredis.from_url",
            return_value=mock_redis_client,
        ):
            store = RedisStore("redis://localhost:6379/0")
            await store.connect()
            mock_redis_client.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_sets_client(self, mock_redis_client):
        with patch(
            "app.memory.stores.redis_store.aioredis.from_url",
            return_value=mock_redis_client,
        ):
            store = RedisStore("redis://localhost:6379/0")
            assert store._client is None
            await store.connect()
            assert store._client is not None

    @pytest.mark.asyncio
    async def test_connect_uses_correct_url(self, mock_redis_client):
        url = "redis://myhost:6380/1"
        with patch(
            "app.memory.stores.redis_store.aioredis.from_url",
            return_value=mock_redis_client,
        ) as mock_from_url:
            store = RedisStore(url)
            await store.connect()
            mock_from_url.assert_called_once()
            assert mock_from_url.call_args[0][0] == url

    # -----------------------------------------------------------------------
    # disconnect()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_disconnect_calls_aclose(self, store, mock_redis_client):
        await store.disconnect()
        mock_redis_client.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_does_nothing_when_not_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        # should not raise
        await store.disconnect()

    # -----------------------------------------------------------------------
    # get()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_get_returns_value(self, store, mock_redis_client):
        mock_redis_client.get = AsyncMock(return_value="stored_value")
        result = await store.get("my-key")
        assert result == "stored_value"

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing_key(self, store, mock_redis_client):
        mock_redis_client.get = AsyncMock(return_value=None)
        result = await store.get("missing-key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_calls_correct_key(self, store, mock_redis_client):
        await store.get("session:user-123")
        mock_redis_client.get.assert_called_once_with("session:user-123")

    @pytest.mark.asyncio
    async def test_get_raises_when_not_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="not connected"):
            await store.get("key")

    # -----------------------------------------------------------------------
    # set()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_set_without_ttl_calls_set(self, store, mock_redis_client):
        await store.set("key", "value")
        mock_redis_client.set.assert_called_once_with("key", "value", ex=None)


    @pytest.mark.asyncio
    async def test_set_raises_when_not_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="not connected"):
            await store.set("key", "value")

    # -----------------------------------------------------------------------
    # delete()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_delete_calls_correct_key(self, store, mock_redis_client):
        await store.delete("session:user-123")
        mock_redis_client.delete.assert_called_once_with("session:user-123")

    @pytest.mark.asyncio
    async def test_delete_raises_when_not_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="not connected"):
            await store.delete("key")

    # -----------------------------------------------------------------------
    # exists()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_exists_returns_true_when_key_present(self, store, mock_redis_client):
        mock_redis_client.exists = AsyncMock(return_value=1)
        result = await store.exists("key")
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_returns_false_when_key_missing(
        self, store, mock_redis_client
    ):
        mock_redis_client.exists = AsyncMock(return_value=0)
        result = await store.exists("key")
        assert result is False

    @pytest.mark.asyncio
    async def test_exists_raises_when_not_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="not connected"):
            await store.exists("key")

    # -----------------------------------------------------------------------
    # expire()
    # -----------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_expire_calls_correct_key_and_ttl(self, store, mock_redis_client):
        await store.expire("session:user-123")
        mock_redis_client.expire.assert_called_once_with("session:user-123")

    @pytest.mark.asyncio
    async def test_expire_raises_when_not_connected(self):
        store = RedisStore("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="not connected"):
            await store.expire("key")

    # -----------------------------------------------------------------------
    # _assert_connected()
    # -----------------------------------------------------------------------

    def test_assert_connected_raises_with_helpful_message(self):
        store = RedisStore("redis://localhost:6379/0")
        with pytest.raises(RuntimeError, match="Call connect\\(\\) before use"):
            store._assert_connected()

    def test_assert_connected_does_not_raise_when_connected(self, store):
        # should not raise — client is set by the fixture
        store._assert_connected()
