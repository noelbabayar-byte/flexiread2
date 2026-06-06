"""
Pydantic schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int  # Seconds


class TokenPayload(BaseModel):
    """JWT token payload."""

    sub: str  # User ID
    exp: datetime
    iat: datetime


class UserRegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)


class UserLoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class UserOut(BaseModel):
    """User response (no sensitive data)."""

    id: UUID
    email: str
    full_name: Optional[str]
    plan_type: str
    ocr_quota_remaining: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    """Refresh token exchange request."""

    refresh_token: str
