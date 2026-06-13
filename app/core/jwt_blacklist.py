"""
Redis-backed JWT blacklist support.

Tokens are stored by their JWT ID (``jti``) until their natural expiry time.
The implementation is intentionally fail-closed for blacklist checks so a Redis
outage does not accidentally allow a revoked token.
"""

from datetime import datetime, timezone
import logging
from typing import Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)


class JWTBlacklist:
    """Persist revoked JWT identifiers in Redis with an expiry TTL."""

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis = redis_client or redis.from_url(settings.REDIS_URL)
        self.prefix = "jwt_blacklist:"

    def blacklist_token(self, jti: str, exp: datetime) -> None:
        """Blacklist a token identifier until the token expiration time."""
        if not jti:
            return

        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)

        ttl = int((exp - datetime.now(timezone.utc)).total_seconds())
        if ttl <= 0:
            return

        try:
            self.redis.setex(f"{self.prefix}{jti}", ttl, "1")
            logger.info("JWT token blacklisted: %s", jti)
        except Exception as exc:  # pragma: no cover - infrastructure failure path
            logger.error("Failed to blacklist JWT token: %s", exc)
            raise

    def is_blacklisted(self, jti: str) -> bool:
        """Return True when a JWT identifier has been revoked."""
        if not jti:
            return False

        try:
            return bool(self.redis.exists(f"{self.prefix}{jti}"))
        except Exception as exc:  # pragma: no cover - infrastructure failure path
            logger.error("JWT blacklist check failed: %s", exc)
            # Fail-closed: if we cannot confirm a token is clean, treat it as
            # revoked. This matches the security intent in the module docstring;
            # a Redis outage already degrades the whole app (broker, rate limiter,
            # progress) so denying tokens does not uniquely brick it.
            return True


jwt_blacklist = JWTBlacklist()
