"""
Security utilities for authentication and authorization.
Handles JWT token generation/validation and password hashing.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class SecurityManager:
    """Manages JWT tokens and password hashing."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash.

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: dict, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create JWT access token.

        Args:
            data: Dictionary to encode in token
            expires_delta: Token expiration time

        Returns:
            JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                hours=settings.JWT_EXPIRATION_HOURS
            )

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "jti": str(uuid.uuid4()),
                "type": "access",
            }
        )

        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """
        Create JWT refresh token.

        Args:
            data: Dictionary to encode in token

        Returns:
            JWT refresh token string
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_EXPIRATION_DAYS
        )
        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "jti": str(uuid.uuid4()),
                "type": "refresh",
            }
        )

        encoded_jwt = jwt.encode(
            to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM
        )

        return encoded_jwt

    @staticmethod
    def verify_token(token: str) -> Optional[dict]:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token data if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
            )
            jti = payload.get("jti")
            if jti:
                from app.core.jwt_blacklist import jwt_blacklist

                if jwt_blacklist.is_blacklisted(jti):
                    logger.warning("Token has been revoked: %s", jti)
                    return None
            return payload
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None


# Global security manager instance
security_manager = SecurityManager()
