import logging
from unittest.mock import Mock
import pytest


def test_unavailable_redis_warning_contains_exception(monkeypatch, caplog):
    monkeypatch.setattr("redis.from_url", Mock(side_effect=ConnectionError("connection refused")))
    from app.cache.redis_cache import RedisCache

    with caplog.at_level(logging.WARNING, logger="app"):
        cache = RedisCache()

    assert cache.client is None
    assert cache.is_connected is False
    assert "connection refused" in caplog.text
    assert "Falling back to no-cache mode" in caplog.text


@pytest.fixture
def connected_cache(monkeypatch):
    client = Mock()
    monkeypatch.setattr("redis.from_url", Mock(return_value=client))
    from app.cache.redis_cache import RedisCache

    return RedisCache(), client


def test_cache_reads_utf8_and_handles_misses(connected_cache):
    cache, client = connected_cache
    client.get.side_effect = [b'{"result": 1}', None]
    assert cache.get("hit") == '{"result": 1}'
    assert cache.get("miss") is None
    client.get.assert_any_call("hit")
    client.get.assert_any_call("miss")


def test_cache_passes_expiration_to_redis(connected_cache):
    cache, client = connected_cache
    assert cache.set("key", "value", expire_seconds=42) is True
    client.set.assert_called_once_with("key", "value", ex=42)


def test_disconnected_cache_skips_reads_and_writes(connected_cache):
    cache, client = connected_cache
    cache.is_connected = False
    assert cache.get("key") is None
    assert cache.set("key", "value") is False
    client.get.assert_not_called()
    client.set.assert_not_called()


def test_redis_read_failure_returns_miss_and_logs_error(connected_cache, caplog):
    cache, client = connected_cache
    client.get.side_effect = RuntimeError("read unavailable")
    assert cache.get("key") is None
    assert "read unavailable" in caplog.text


def test_redis_write_failure_returns_false_and_logs_error(connected_cache, caplog):
    cache, client = connected_cache
    client.set.side_effect = RuntimeError("write unavailable")
    assert cache.set("key", "value") is False
    assert "write unavailable" in caplog.text
