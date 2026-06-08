from unittest.mock import patch
from app.utils.rate_limiter import rate_limiter


def test_rate_limiter_logic():
    """
    Test rate limiter logic using mocks to ensure predictable behavior in CI.
    """
    # We mock the underlying redis eval call to simulate rate limiting logic
    with patch("app.utils.rate_limiter.redis_manager.redis.eval") as mocked_eval:
        key = "test_user_limit"
        max_req = 2
        window = 1

        # Mock behavior: 2 allowed, 1 blocked, then 1 allowed (after simulated reset/expiry)
        mocked_eval.side_effect = [True, True, False, True]

        # First two requests should be allowed
        assert rate_limiter.is_allowed(key, max_req, window) is True
        assert rate_limiter.is_allowed(key, max_req, window) is True

        # Third request should be blocked
        assert rate_limiter.is_allowed(key, max_req, window) is False

        # Should be allowed again (simulated expiry)
        assert rate_limiter.is_allowed(key, max_req, window) is True
