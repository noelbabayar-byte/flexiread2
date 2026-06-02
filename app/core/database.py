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
# MVP: Keep pool small to avoid "too many clients" errors on cheap RDS/Supabase
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,  # Number of connections to keep in the pool
    max_overflow=5,  # Maximum overflow connections
    pool_pre_ping=True,  # Verify connections before using them
    echo=settings.DEBUG,  # Log SQL queries in debug mode
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
