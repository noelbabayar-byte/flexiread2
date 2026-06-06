"""
Rate limiting utilities using Redis.
"""

import redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL)


class RateLimiter:
    """Redis-based rate limiter."""

    @staticmethod
    def is_allowed(key: str, max_requests: int, window_seconds: int) -> bool:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Unique identifier (e.g., "user_123:process_pdf")
            max_requests: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            True if request is allowed, False if rate limited
        """
        try:
            lua_script = (
                "local current = redis.call('INCR', KEYS[1]); "
                "if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end; "
                "return current <= tonumber(ARGV[2])"
            )
            result = redis_client.eval(lua_script, 1, key, window_seconds, max_requests)
            return bool(result)
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # On error, fail-closed for security
            return False

    @staticmethod
    def get_remaining(key: str, max_requests: int) -> int:
        """
        Get remaining requests in current window.

        Args:
            key: Unique identifier
            max_requests: Maximum requests allowed

        Returns:
            Number of remaining requests
        """
        try:
            current = redis_client.get(key)
            if current is None:
                return max_requests

            current_int = int(current)
            remaining = max(0, max_requests - current_int)
            return remaining
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return 0  # Fail-closed for remaining count as well

    @staticmethod
    def reset(key: str) -> None:
        """
        Reset rate limit for key.

        Args:
            key: Unique identifier
        """
        try:
            redis_client.delete(key)
        except Exception as e:
            logger.error(f"Rate limiter reset error: {e}")


# Global rate limiter instance
rate_limiter = RateLimiter()
