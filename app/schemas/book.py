"""
Pydantic schemas for Book model validation.
Used for API request/response serialization.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from app.models.book import BookStatus


class BookUploadRequest(BaseModel):
    """Schema for PDF upload request."""
    title: str = Field(..., min_length=1, max_length=255)


class BookStatusResponse(BaseModel):
    """Schema for book processing status response."""
    id: str
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
    """Schema for processed book content response."""
    id: str
    title: str
    status: BookStatus
    parsed_content_url: Optional[str]
    total_pages: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class BookListResponse(BaseModel):
    """Schema for book list response."""
    id: str
    title: str
    status: BookStatus
    progress_percentage: int
    total_pages: int
    created_at: datetime
    
    class Config:
        from_attributes = True
