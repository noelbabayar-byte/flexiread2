"""
User model for authentication and subscription management.
Stores user credentials, subscription tier, and OCR quota tracking.
"""

from sqlalchemy import Column, String, Enum, Integer, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class SubscriptionTier(str, enum.Enum):
    """Subscription tier enumeration."""

    FREE = "free"
    PRO = "pro"


class User(BaseModel):
    """
    User model for authentication and profile management.

    Attributes:
        email: Unique user email
        password_hash: Bcrypt hashed password
        full_name: User's full name
        plan_type: Subscription tier (free/pro)
        ocr_quota_remaining: Pages remaining in current month
        ocr_quota_reset_date: Date when quota resets
        is_active: Account status
        books: Relationship to user's books
    """

    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    plan_type = Column(
        Enum(SubscriptionTier), default=SubscriptionTier.FREE, nullable=False
    )

    # OCR Quota tracking
    ocr_quota_remaining = Column(Integer, default=50, nullable=False)  # Pages
    ocr_quota_reset_date = Column(DateTime, nullable=False)  # When quota resets next

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    books = relationship("Book", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, plan={self.plan_type.value})>"

    def has_quota(self, pages_needed: int = 1) -> bool:
        """
        Check if user has enough OCR quota.

        Args:
            pages_needed: Number of pages to process

        Returns:
            True if user has enough quota, False otherwise
        """
        return self.ocr_quota_remaining >= pages_needed

    def consume_quota(self, pages_needed: int) -> bool:
        """
        Consume OCR quota for processed pages.

        Args:
            pages_needed: Number of pages to deduct from quota

        Returns:
            True if quota consumed successfully, False otherwise
        """
        if not self.has_quota(pages_needed):
            return False
        self.ocr_quota_remaining -= pages_needed
        if self.ocr_quota_remaining < 0:
            self.ocr_quota_remaining = 0
        return True
