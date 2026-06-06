"""
Application Configuration
Supports both local development and GitHub Codespaces environments
"""

import os
import secrets
from typing import Optional, List, Any
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ValidationInfo


class Settings(BaseSettings):
    """Application settings with environment detection"""

    # ========================================================================
    # Environment Detection
    # ========================================================================
    ENVIRONMENT: str = Field(default="development", description="Environment type")
    CODESPACES: bool = Field(default=False, description="Running in GitHub Codespaces")
    CODESPACE_NAME: Optional[str] = Field(default=None, description="Codespaces name")
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # ========================================================================
    # Database Configuration
    # ========================================================================
    DB_USER: str = Field(default="flexiread", description="Database user")
    DB_PASSWORD: str = Field(
        default="flexiread_dev_password", description="Database password"
    )
    DB_NAME: str = Field(default="flexiread", description="Database name")
    DB_HOST: str = Field(default="db", description="Database host")
    DB_PORT: int = Field(default=5432, description="Database port")
    DATABASE_URL: Optional[str] = Field(default=None, description="Full database URL")

    # Database connection pool
    DB_POOL_SIZE: int = Field(default=20, description="Database pool size")
    DB_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow")
    DB_POOL_RECYCLE: int = Field(default=3600, description="Database pool recycle time")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries")

    # ========================================================================
    # Redis Configuration
    # ========================================================================
    REDIS_HOST: str = Field(default="redis", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_PASSWORD: str = Field(
        default="flexiread_redis_dev", description="Redis password"
    )
    REDIS_DB: int = Field(default=0, description="Redis database number")
    REDIS_URL: Optional[str] = Field(default=None, description="Full Redis URL")

    # ========================================================================
    # Celery Configuration
    # ========================================================================
    CELERY_BROKER_URL: Optional[str] = Field(
        default=None, description="Celery broker URL"
    )
    CELERY_RESULT_BACKEND: Optional[str] = Field(
        default=None, description="Celery result backend"
    )
    CELERY_WORKER_CONCURRENCY: int = Field(
        default=1, description="Celery worker concurrency"
    )
    CELERY_TASK_TIMEOUT: int = Field(default=3600, description="Celery task timeout")

    # ========================================================================
    # JWT & Authentication
    # ========================================================================
    JWT_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32), description="JWT secret key"
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_HOURS: int = Field(default=24, description="JWT expiration hours")
    JWT_REFRESH_EXPIRATION_DAYS: int = Field(
        default=7, description="JWT refresh expiration days"
    )

    # ========================================================================
    # AWS S3 / MinIO Configuration
    # ========================================================================
    # Internal endpoint (Docker network) - used by backend/worker
    AWS_S3_INTERNAL_ENDPOINT_URL: str = Field(
        default="http://minio:9000", description="S3 internal endpoint (Docker network)"
    )

    # Public endpoint (Browser/Frontend) - used for presigned URLs
    AWS_S3_PUBLIC_ENDPOINT_URL: Optional[str] = Field(
        default=None, description="S3 public endpoint (Browser access)"
    )

    # Common S3 settings
    AWS_ACCESS_KEY_ID: str = Field(default="minioadmin", description="AWS access key")
    AWS_SECRET_ACCESS_KEY: str = Field(
        default="minioadmin", description="AWS secret key"
    )
    AWS_S3_BUCKET: str = Field(default="flexiread-dev", description="S3 bucket name")
    AWS_S3_REGION: str = Field(default="us-east-1", description="AWS region")

    # ========================================================================
    # Public URLs (for Frontend and API responses)
    # ========================================================================
    PUBLIC_API_URL: Optional[str] = Field(
        default=None, description="Public API URL (for frontend)"
    )
    PUBLIC_S3_URL: Optional[str] = Field(
        default=None, description="Public S3 URL (for presigned URLs)"
    )
    PUBLIC_FRONTEND_URL: Optional[str] = Field(
        default=None, description="Public Frontend URL (for CORS)"
    )

    # ========================================================================
    # Application Configuration
    # ========================================================================
    APP_NAME: str = Field(default="FlexiRead", description="Application name")
    APP_ENV: str = Field(default="development", description="Application environment")

    # ========================================================================
    # CORS Configuration
    # ========================================================================
    ALLOWED_ORIGINS: Any = Field(
        default="http://localhost:5173,http://localhost:3000",
        description="Allowed CORS origins (comma-separated or list)",
    )

    # ========================================================================
    # Rate Limiting
    # ========================================================================
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="Rate limit requests")
    RATE_LIMIT_PERIOD_SECONDS: int = Field(default=60, description="Rate limit period")

    # ========================================================================
    # PDF Processing
    # ========================================================================
    MAX_PDF_SIZE_MB: int = Field(default=150, description="Max PDF size in MB")
    OCR_ENABLED: bool = Field(default=True, description="Enable OCR")
    OCR_LANGUAGE: str = Field(default="tur,eng", description="OCR languages")
    OCR_TIMEOUT_SECONDS: int = Field(default=300, description="OCR timeout")
    TESSERACT_CMD: str = Field(
        default="/usr/bin/tesseract", description="Tesseract OCR command path"
    )

    # ========================================================================
    # Subscription & Pricing
    # ========================================================================
    FREE_TIER_MONTHLY_QUOTA: int = Field(
        default=50, description="Free tier monthly quota"
    )
    PRO_TIER_MONTHLY_QUOTA: int = Field(
        default=1000, description="Pro tier monthly quota"
    )
    PRO_TIER_PRICE_USD: float = Field(default=9.99, description="Pro tier price in USD")

    # ========================================================================
    # Frontend Configuration
    # ========================================================================
    VITE_API_URL: Optional[str] = Field(default=None, description="Vite API URL")
    VITE_API_TIMEOUT: int = Field(default=30000, description="Vite API timeout")
    VITE_ENV: str = Field(default="development", description="Vite environment")

    # ========================================================================
    # Feature Flags
    # ========================================================================
    FEATURE_OFFLINE_READING: bool = Field(
        default=True, description="Offline reading feature"
    )
    FEATURE_ANNOTATIONS: bool = Field(default=True, description="Annotations feature")
    FEATURE_COLLABORATION: bool = Field(
        default=False, description="Collaboration feature"
    )
    FEATURE_EXPORT_PDF: bool = Field(default=True, description="Export PDF feature")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }

    # ========================================================================
    # Validators and Post-Init Logic
    # ========================================================================

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Ensure JWT secrets meet the minimum production safety length."""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Build DATABASE_URL if not provided"""
        if v:
            return v

        data = info.data
        db_user = data.get("DB_USER", "flexiread")
        db_password = data.get("DB_PASSWORD", "flexiread_dev_password")
        db_host = data.get("DB_HOST", "db")
        db_port = data.get("DB_PORT", 5432)
        db_name = data.get("DB_NAME", "flexiread")

        return f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def build_redis_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Build REDIS_URL if not provided"""
        if v:
            return v

        data = info.data
        redis_password = data.get("REDIS_PASSWORD", "flexiread_redis_dev")
        redis_host = data.get("REDIS_HOST", "redis")
        redis_port = data.get("REDIS_PORT", 6379)
        redis_db = data.get("REDIS_DB", 0)

        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def build_celery_broker_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Build CELERY_BROKER_URL if not provided"""
        if v:
            return v
        return info.data.get("REDIS_URL") or "redis://:flexiread_redis_dev@redis:6379/0"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def build_celery_result_backend(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Build CELERY_RESULT_BACKEND if not provided"""
        if v:
            return v
        redis_url = (
            info.data.get("REDIS_URL") or "redis://:flexiread_redis_dev@redis:6379/0"
        )
        return redis_url.replace("/0", "/1")

    @field_validator("AWS_S3_PUBLIC_ENDPOINT_URL", mode="before")
    @classmethod
    def set_public_s3_endpoint(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Set public S3 endpoint based on environment"""
        if v:
            return v

        data = info.data
        # If in Codespaces, use the public URL
        if data.get("CODESPACES"):
            codespace_name = data.get("CODESPACE_NAME", "flexiread")
            return f"https://{codespace_name}-9000.github.dev"

        # Otherwise, use localhost
        return "http://localhost:9000"

    @field_validator("PUBLIC_API_URL", mode="before")
    @classmethod
    def set_public_api_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Set public API URL based on environment"""
        if v:
            return v

        data = info.data
        # If in Codespaces, use the public URL
        if data.get("CODESPACES"):
            codespace_name = data.get("CODESPACE_NAME", "flexiread")
            return f"https://{codespace_name}-8000.github.dev"

        # Otherwise, use localhost
        return "http://localhost:8000"

    @field_validator("PUBLIC_FRONTEND_URL", mode="before")
    @classmethod
    def set_public_frontend_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Set public frontend URL based on environment"""
        if v:
            return v

        data = info.data
        # If in Codespaces, use the public URL
        if data.get("CODESPACES"):
            codespace_name = data.get("CODESPACE_NAME", "flexiread")
            return f"https://{codespace_name}-5173.github.dev"

        # Otherwise, use localhost
        return "http://localhost:5173"

    @field_validator("VITE_API_URL", mode="before")
    @classmethod
    def set_vite_api_url(cls, v: Optional[str], info: ValidationInfo) -> str:
        """Set Vite API URL (same as PUBLIC_API_URL)"""
        if v:
            return v
        return info.data.get("PUBLIC_API_URL") or "http://localhost:8000"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def build_allowed_origins(cls, v: Any, info: ValidationInfo) -> List[str]:
        """Build ALLOWED_ORIGINS list"""
        origins = []
        if isinstance(v, str):
            origins = [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            origins = v

        data = info.data
        # Add public frontend URL if in Codespaces
        if data.get("CODESPACES"):
            public_frontend = data.get("PUBLIC_FRONTEND_URL")
            if public_frontend and public_frontend not in origins:
                origins.append(public_frontend)

        return origins

    def get_allowed_origins_list(self) -> list:
        """Get ALLOWED_ORIGINS as a list"""
        if isinstance(self.ALLOWED_ORIGINS, list):
            return self.ALLOWED_ORIGINS
        return [o.strip() for o in str(self.ALLOWED_ORIGINS).split(",")]

    def is_codespaces(self) -> bool:
        """Check if running in Codespaces"""
        return self.CODESPACES or os.getenv("CODESPACES") == "true"

    def is_production(self) -> bool:
        """Check if running in production"""
        return self.APP_ENV == "production"

    def is_development(self) -> bool:
        """Check if running in development"""
        return self.APP_ENV in ["development", "codespaces"]


# Create global settings instance
settings = Settings()
