"""
Database configuration and session management.
Handles PostgreSQL connection pooling and session lifecycle.
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Create database engine with connection pooling
# Optimized pool settings based on Part 1 requirements
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DB_POOL_SIZE,  # Use value from settings
    max_overflow=settings.DB_MAX_OVERFLOW,  # Use value from settings
    pool_pre_ping=True,  # Verify connections before using them
    pool_recycle=settings.DB_POOL_RECYCLE,  # Recycle connections after 1 hour
    echo=settings.DB_ECHO,  # Log SQL queries if configured
    connect_args={
        "connect_timeout": 10,
        "application_name": "flexiread_backend",
    }
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)


def get_db() -> Session:
    """
    Dependency for FastAPI to get database session.
    Ensures session is closed after request.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    Call this once on application startup.
    """
    from app.models.base import Base
    # Models must be imported before create_all
    import app.models.user
    import app.models.book
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")


@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    SQLAlchemy event listener for connection initialization.
    Enables UUID support in PostgreSQL.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
    cursor.close()
