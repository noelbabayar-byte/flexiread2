"""
User profile and quota endpoints.
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserDetailResponse, UserResponse

router = APIRouter(tags=["users"])


class QuotaResponse(BaseModel):
    """OCR quota response for the authenticated user."""

    remaining: int
    total: int
    reset_date: Optional[datetime]
    plan_type: str


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user's public profile."""
    return current_user


@router.get("/quota", response_model=QuotaResponse)
async def get_quota(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's current OCR quota state."""
    total = (
        settings.PRO_TIER_MONTHLY_QUOTA
        if current_user.plan_type.value == "pro"
        else settings.FREE_TIER_MONTHLY_QUOTA
    )
    return QuotaResponse(
        remaining=current_user.ocr_quota_remaining,
        total=total,
        reset_date=current_user.ocr_quota_reset_date,
        plan_type=current_user.plan_type.value,
    )


@router.get("/profile", response_model=UserDetailResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's detailed profile."""
    return current_user
