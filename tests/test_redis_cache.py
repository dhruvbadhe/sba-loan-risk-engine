import logging
from unittest.mock import Mock


def test_unavailable_redis_warning_contains_exception(monkeypatch, caplog):
    monkeypatch.setattr("redis.from_url", Mock(side_effect=ConnectionError("connection refused")))
    from app.cache.redis_cache import RedisCache

    with caplog.at_level(logging.WARNING, logger="app"):
        cache = RedisCache()

    assert cache.client is None
    assert cache.is_connected is False
    assert "connection refused" in caplog.text
    assert "Falling back to no-cache mode" in caplog.text
