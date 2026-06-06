from datetime import datetime, timezone

import factory

from app.core.config import settings
from app.core.security import security_manager
from app.models.book import Book, BookStatus
from app.models.user import SubscriptionTier, User


class UserFactory(factory.Factory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    full_name = factory.Faker("name")
    password_hash = factory.LazyFunction(
        lambda: security_manager.hash_password("password123")
    )
    plan_type = SubscriptionTier.FREE
    ocr_quota_remaining = factory.LazyFunction(lambda: settings.FREE_TIER_MONTHLY_QUOTA)
    ocr_quota_reset_date = factory.LazyFunction(lambda: datetime.now(timezone.utc))
    is_active = True


class BookFactory(factory.Factory):
    class Meta:
        model = Book

    title = factory.Sequence(lambda n: f"Test Book {n}")
    original_filename = factory.Sequence(lambda n: f"test-{n}.pdf")
    status = BookStatus.PENDING
    progress_percentage = 0
    total_pages = 0
    processed_pages = 0
    original_pdf_url = "s3://flexiread-test/uploads/test.pdf"
