"""
Book model for PDF document tracking and processing status.
Stores metadata about uploaded PDFs and their processing state.
"""

from sqlalchemy import (
    Column,
    String,
    Enum,
    Integer,
    ForeignKey,
    Text,
    UUID as SQLAlchemyUUID,
)
from sqlalchemy.orm import relationship
from app.models.base import BaseModel
import enum


class BookStatus(str, enum.Enum):
    """Book processing status enumeration."""

    PENDING = "pending"  # Waiting to be processed
    PROCESSING = "processing"  # Currently being processed
    COMPLETED = "completed"  # Successfully processed
    FAILED = "failed"  # Processing failed


class Book(BaseModel):
    """
    Book model for tracking PDF documents and their OCR processing.

    Attributes:
        user_id: Owner of the book
        title: Book title
        original_filename: Original PDF filename
        status: Current processing status
        progress_percentage: OCR processing progress (0-100)
        total_pages: Total pages in PDF
        processed_pages: Pages successfully processed
        original_pdf_url: S3 URL to original PDF
        parsed_content_url: S3 URL to processed JSON content
        error_message: Error details if processing failed
        owner: Relationship to User
    """

    __tablename__ = "books"

    # Foreign key
    user_id = Column(
        SQLAlchemyUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Book metadata
    title = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)

    # Processing status
    status = Column(
        Enum(BookStatus), default=BookStatus.PENDING, nullable=False, index=True
    )
    progress_percentage = Column(Integer, default=0, nullable=False)  # 0-100

    # Page tracking
    total_pages = Column(Integer, default=0, nullable=False)
    processed_pages = Column(Integer, default=0, nullable=False)

    # S3 URLs
    original_pdf_url = Column(String(512), nullable=False)
    parsed_content_url = Column(String(512), nullable=True)

    # Error handling
    error_message = Column(Text, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="books")

    def __repr__(self) -> str:
        return f"<Book(id={self.id}, title={self.title}, status={self.status.value})>"

    def update_progress(self, processed_pages: int, total_pages: int) -> None:
        """
        Update processing progress.

        Args:
            processed_pages: Number of pages processed so far
            total_pages: Total pages to process
        """
        self.processed_pages = processed_pages
        self.total_pages = total_pages

        if total_pages > 0:
            self.progress_percentage = int((processed_pages / total_pages) * 100)
        else:
            self.progress_percentage = 0

    def mark_completed(self, parsed_content_url: str) -> None:
        """
        Mark book as successfully processed.

        Args:
            parsed_content_url: S3 URL to processed content
        """
        self.status = BookStatus.COMPLETED
        self.progress_percentage = 100
        self.parsed_content_url = parsed_content_url
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        """
        Mark book as failed to process.

        Args:
            error_message: Description of the error
        """
        self.status = BookStatus.FAILED
        self.error_message = error_message
