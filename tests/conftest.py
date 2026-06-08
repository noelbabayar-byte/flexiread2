import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault(
    "DATABASE_URL", "postgresql://test:test@localhost:5432/flexiread_test"
)
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_NAME", "flexiread_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-that-is-longer-than-thirty-two-chars"
)
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_S3_BUCKET", "flexiread-test")
os.environ.setdefault("AWS_S3_INTERNAL_ENDPOINT_URL", "http://localhost:9000")

from app.core.database import get_db  # noqa: E402
from app.core.security import security_manager  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.models.user import SubscriptionTier, User  # noqa: E402

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", os.environ["DATABASE_URL"])

engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


@pytest.fixture(scope="function")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        email="test@example.com",
        password_hash=security_manager.hash_password("password123"),
        full_name="Test User",
        plan_type=SubscriptionTier.FREE,
        ocr_quota_remaining=50,
        ocr_quota_reset_date=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mocked_external_services():
    with patch(
        "app.api.v1.endpoints.books.s3_storage.generate_presigned_url",
        return_value="http://example.com/upload",
    ), patch(
        "app.api.v1.endpoints.books.redis_client.get", return_value=None
    ), patch(
        "app.utils.rate_limiter.redis_manager.redis.eval", return_value=1
    ), patch(
        "app.utils.rate_limiter.redis_manager.redis.get", return_value=None
    ), patch(
        "app.utils.rate_limiter.redis_manager.redis.delete", return_value=1
    ):
        yield
