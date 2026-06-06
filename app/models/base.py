"""
Base model for all SQLAlchemy ORM models.
Provides common fields and functionality.
"""

from sqlalchemy import Column, DateTime, func, UUID
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with common fields.
    All models should inherit from this.
    """

    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        """String representation of model instance."""
        return f"<{self.__class__.__name__}(id={self.id})>"
