"""
Rate limiting utilities using Redis.
"""

import logging
from app.core.redis_client import redis_manager

logger = logging.getLogger(__name__)

# Defined at module level to prevent re-allocation on every method call
LUA_RATE_LIMITER = (
    "local key = KEYS[1]; "
    "local expiry = ARGV[1]; "
    "local threshold = tonumber(ARGV[2]); "
    "local current = redis.call('INCR', key); "
    "if current == 1 then redis.call('EXPIRE', key, expiry) end; "
    "return current <= threshold"
)


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
            # Execute the optimized Lua script via redis_manager
            result = redis_manager.redis.eval(
                LUA_RATE_LIMITER, 1, key, window_seconds, max_requests
            )

            logger.debug(f"Rate limit check: key={key}, allowed={bool(result)}")
            return bool(result)
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Fail-open in production to avoid blocking users during Redis issues
            return True

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
            current = redis_manager.redis.get(key)
            if current is None:
                return max_requests

            current_int = int(current)
            remaining = max(0, max_requests - current_int)
            return remaining
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return 0

    @staticmethod
    def reset(key: str) -> None:
        """
        Reset rate limit for key.

        Args:
            key: Unique identifier
        """
        try:
            redis_manager.redis.delete(key)
        except Exception as e:
            logger.error(f"Rate limiter reset error: {e}")


# Global rate limiter instance
rate_limiter = RateLimiter()
