"""
Pydantic schemas for book endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.models.book import BookStatus


class PresignedURLRequest(BaseModel):
    """Request for presigned URL generation."""

    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)  # File size in bytes
    title: Optional[str] = Field(None, max_length=255)


class PresignedURLResponse(BaseModel):
    """Presigned URL response."""

    book_id: str
    presigned_url: str
    s3_key: str
    expires_in: int  # Seconds


class BookStatusResponse(BaseModel):
    """Book processing status response."""

    id: UUID
    title: str
    status: BookStatus
    progress_percentage: int
    total_pages: int
    processed_pages: int
    error_message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BookContentResponse(BaseModel):
    """Book content response."""

    id: UUID
    title: str
    status: BookStatus
    total_pages: int
    content_summary: Optional[str] = None

    class Config:
        from_attributes = True


class ProcessBookRequest(BaseModel):
    """Request to process uploaded book."""

    book_id: str


class ProcessBookResponse(BaseModel):
    """Response for process book request."""

    book_id: str
    status: str
    task_id: str
    message: str
