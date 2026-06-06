from app.utils.rate_limiter import rate_limiter


def test_rate_limiter_allowed(monkeypatch):
    monkeypatch.setattr(
        "app.utils.rate_limiter.redis_client.eval", lambda *args, **kwargs: 1
    )

    assert rate_limiter.is_allowed("test_key", 10, 60) is True


def test_rate_limiter_exceeded(monkeypatch):
    monkeypatch.setattr(
        "app.utils.rate_limiter.redis_client.eval", lambda *args, **kwargs: 0
    )

    assert rate_limiter.is_allowed("test_key_exceeded", 10, 60) is False


def test_rate_limiter_remaining(monkeypatch):
    monkeypatch.setattr("app.utils.rate_limiter.redis_client.get", lambda key: b"3")

    assert rate_limiter.get_remaining("test_key", 10) == 7
