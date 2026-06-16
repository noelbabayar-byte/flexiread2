"""
Book endpoints: Upload, Status, and Content retrieval.
Handles PDF upload with presigned URLs, processing status, and content delivery.
"""

import json
import logging
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from sqlalchemy import func, update
import redis
from app.core.database import get_db
from app.core.config import settings
from app.models.user import User, SubscriptionTier
from app.models.book import Book, BookStatus
from app.api.dependencies import get_current_user
from app.schemas.books import (
    PresignedURLRequest,
    PresignedURLResponse,
    BookStatusResponse,
    BookContentResponse,
    ProcessBookResponse,
    BookListResponse,
)
from app.utils.s3_storage import s3_storage
from app.utils.rate_limiter import rate_limiter
from worker.tasks import process_pdf_task
import os
import tempfile
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(tags=["books"])

# Redis client for progress tracking
redis_client = redis.from_url(settings.REDIS_URL)

# File size limits (in bytes)
FREE_TIER_MAX_SIZE = 50 * 1024 * 1024  # 50 MB
PRO_TIER_MAX_SIZE = 200 * 1024 * 1024  # 200 MB


@router.get("/", response_model=BookListResponse)
async def list_books(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all books for the current user with optimized pagination.
    """
    # 1. Optimized Count Query using Primary Key directly
    total = (
        db.query(func.count(Book.id)).filter(Book.user_id == current_user.id).scalar()
        or 0
    )

    # 2. Paginated Data Query
    books = (
        db.query(Book)
        .filter(Book.user_id == current_user.id)
        .order_by(Book.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # 3. Predictable page calculation mapping
    current_page = (skip // limit) + 1 if limit > 0 else 1

    return {
        "items": [
            BookStatusResponse.model_validate(b, from_attributes=True) for b in books
        ],
        "total": total,
        "page": current_page,
        "size": limit,
    }


@router.post("/upload-url", response_model=PresignedURLResponse)
async def get_upload_url(
    request: PresignedURLRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate presigned URL for direct S3 upload.

    Frontend uploads file directly to S3 using this URL.
    Validates file extension, size, and user quota.

    Args:
        request: Upload request with filename and size
        current_user: Authenticated user
        db: Database session

    Returns:
        Presigned URL and book ID

    Raises:
        HTTPException 400: Invalid file extension
        HTTPException 413: File too large
        HTTPException 403: Insufficient quota
    """
    try:
        # Step 1: Validate file extension
        if not request.filename.lower().endswith(".pdf"):
            logger.warning(f"Invalid file extension: {request.filename}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed",
            )

        # Step 2: Validate file size based on subscription tier
        if current_user.plan_type == SubscriptionTier.FREE:
            if request.file_size > FREE_TIER_MAX_SIZE:
                logger.warning(
                    f"Free user exceeded size limit: {current_user.email} "
                    f"({request.file_size} bytes)"
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Free tier maximum file size is 50 MB",
                )
        else:  # Pro tier
            if request.file_size > PRO_TIER_MAX_SIZE:
                logger.warning(
                    f"Pro user exceeded size limit: {current_user.email} "
                    f"({request.file_size} bytes)"
                )
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Pro tier maximum file size is 200 MB",
                )

        # Step 3: Check OCR quota
        if current_user.ocr_quota_remaining <= 0:
            logger.warning(f"User out of quota: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient OCR quota. Please upgrade to Pro.",
            )

        # Step 4: Create book record
        book_id = uuid.uuid4()
        title = request.title or request.filename.replace(".pdf", "")

        book = Book(
            id=book_id,
            user_id=current_user.id,
            title=title,
            original_filename=request.filename,
            status=BookStatus.PENDING,
            original_pdf_url=(
                f"s3://{settings.AWS_S3_BUCKET}/uploads/"
                f"{current_user.id}/{book_id}/{request.filename}"
            ),
        )

        db.add(book)
        db.commit()

        # Step 5: Generate presigned URL
        s3_key = f"uploads/{current_user.id}/{book_id}/{request.filename}"
        presigned_url = s3_storage.generate_presigned_url(s3_key, expiration=3600)

        if not presigned_url:
            logger.error(f"Failed to generate presigned URL for: {s3_key}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate upload URL",
            )

        logger.info(
            f"Presigned URL generated: user={current_user.email}, "
            f"book={book_id}, size={request.file_size} bytes"
        )

        return PresignedURLResponse(
            book_id=str(book_id),
            presigned_url=presigned_url,
            s3_key=s3_key,
            expires_in=3600,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload URL generation failed: {e}")
        # db.rollback() KALDIR - get_db dependency'si zaten yapıyor
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )


@router.post("/process/{book_id}", response_model=ProcessBookResponse)
async def process_book(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Trigger PDF processing after successful S3 upload.

    Rate limited: Maximum 2 requests per minute per user.

    Args:
        book_id: Book ID to process
        current_user: Authenticated user
        db: Database session

    Returns:
        Processing task info

    Raises:
        HTTPException 404: Book not found
        HTTPException 403: Not book owner or rate limited
        HTTPException 409: Book already processing
    """
    try:
        # Validate UUID format
        try:
            book_uuid = uuid.UUID(book_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid book ID format"
            )

        # Step 1: Rate limiting
        rate_limit_key = f"user:{current_user.id}:process_pdf"
        if not rate_limiter.is_allowed(
            rate_limit_key, max_requests=2, window_seconds=60
        ):
            logger.warning(f"Rate limit exceeded: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many processing requests. Maximum 2 per minute.",
            )

        # Step 2: Fetch book
        book = db.query(Book).filter(Book.id == book_uuid).first()
        if not book:
            logger.warning(f"Book not found: {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )

        # Step 3: Verify ownership
        if book.user_id != current_user.id:
            logger.warning(
                f"Unauthorized access attempt: user={current_user.email}, "
                f"book={book_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to process this book",
            )

        # Step 4: Atomically claim the book for processing.
        # A plain check-then-set is racy: two concurrent requests can both read
        # PENDING and enqueue duplicate tasks. This conditional UPDATE only
        # transitions PENDING/FAILED -> PROCESSING and lets the database arbitrate.
        claim = db.execute(
            update(Book)
            .where(
                Book.id == book_uuid,
                Book.status.in_([BookStatus.PENDING, BookStatus.FAILED]),
            )
            .values(status=BookStatus.PROCESSING)
        )
        db.commit()

        if claim.rowcount == 0:
            # The claim failed: the book is already PROCESSING or COMPLETED.
            db.refresh(book)
            if book.status == BookStatus.COMPLETED:
                detail = "Book has already been processed"
            else:
                detail = "Book is already being processed"
            logger.warning(f"Could not claim book {book_id}: status={book.status}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

        # Step 5: Trigger Celery task
        s3_key = f"uploads/{current_user.id}/{book_id}/{book.original_filename}"

        task = process_pdf_task.delay(
            book_id=str(book_id), s3_pdf_key=s3_key, user_id=str(current_user.id)
        )

        logger.info(
            f"PDF processing triggered: user={current_user.email}, "
            f"book={book_id}, task={task.id}"
        )

        return ProcessBookResponse(
            book_id=str(book_id),
            status="processing",
            task_id=task.id,
            message="PDF processing started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Process book failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start processing",
        )


@router.get("/{book_id}/status", response_model=BookStatusResponse)
async def get_book_status(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get book processing status.

    CRITICAL: Reads from Redis first (fast), falls back to DB.
    Avoids database load for frequent polling.

    Args:
        book_id: Book ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Book status with progress percentage

    Raises:
        HTTPException 404: Book not found
        HTTPException 403: Not book owner
    """
    try:
        # Validate UUID format
        try:
            book_uuid = uuid.UUID(book_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid book ID format"
            )

        # Step 1: Fetch book from database
        book = db.query(Book).filter(Book.id == book_uuid).first()
        if not book:
            logger.warning(f"Book not found: {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )

        # Step 2: Verify ownership
        if book.user_id != current_user.id:
            logger.warning(
                f"Unauthorized access attempt: user={current_user.email}, "
                f"book={book_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this book",
            )

        # Step 3: Try to get progress from Redis (CRITICAL OPTIMIZATION)
        progress_key = f"book_progress:{book_id}"
        redis_progress = redis_client.get(progress_key)

        if redis_progress:
            try:
                progress_data = json.loads(redis_progress)
                # Update response with Redis data (real-time)
                book.progress_percentage = progress_data.get("progress_percentage", 0)
                book.processed_pages = progress_data.get("current_page", 0)
                logger.debug(f"Progress from Redis: {book_id}")
            except json.JSONDecodeError:
                logger.warning(f"Invalid Redis progress data: {book_id}")

        # If not in Redis, use database values (fallback)

        logger.debug(
            f"Status retrieved: {book_id}, progress={book.progress_percentage}%"
        )

        return BookStatusResponse.model_validate(book, from_attributes=True)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get book status failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get book status",
        )


@router.get("/{book_id}/content", response_model=BookContentResponse)
async def get_book_content(
    book_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get processed book content.

    Only available after processing is completed.
    Fetches content from S3 and returns as JSON.

    Args:
        book_id: Book ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Book content with pages and metadata

    Raises:
        HTTPException 404: Book not found
        HTTPException 403: Not book owner
        HTTPException 409: Book not yet processed
        HTTPException 500: Failed to retrieve content
    """
    try:
        # Validate UUID format
        try:
            book_uuid = uuid.UUID(book_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid book ID format"
            )

        # Step 1: Fetch book
        book = db.query(Book).filter(Book.id == book_uuid).first()
        if not book:
            logger.warning(f"Book not found: {book_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )

        # Step 2: Verify ownership
        if book.user_id != current_user.id:
            logger.warning(
                f"Unauthorized access attempt: user={current_user.email}, "
                f"book={book_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this book",
            )

        # Step 3: Check if processing is complete
        if book.status != BookStatus.COMPLETED:
            logger.warning(f"Book not completed: {book_id}, status={book.status}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Book processing not complete. Current status: {book.status}",
            )

        # Step 4: Fetch content from S3
        if not book.parsed_content_url:
            logger.error(f"No content URL for completed book: {book_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Content not available",
            )

        # Step 5: Fetch the processed JSON content from S3 and return it.
        # parsed_content_url is an s3:// URL; strip the scheme+bucket to get the key.
        bucket_prefix = f"s3://{settings.AWS_S3_BUCKET}/"
        content_key = book.parsed_content_url
        if content_key.startswith(bucket_prefix):
            content_key = content_key[len(bucket_prefix) :]

        content = s3_storage.download_json(content_key)
        if content is None:
            logger.error(f"Failed to fetch content from S3: {content_key}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve book content",
            )

        logger.info(f"Content retrieved: {book_id}")

        return BookContentResponse(
            id=book.id,
            title=book.title,
            status=book.status,
            total_pages=book.total_pages,
            metadata=content.get("metadata"),
            summary=content.get("summary"),
            pages=content.get("pages"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get book content failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve book content",
        )


# =============================================================================
# Direct upload endpoint (bypasses S3 CORS issues)
# =============================================================================


@router.post("/upload", response_model=ProcessBookResponse)
async def upload_book(
    file: UploadFile = File(...),
    title: str = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(400, detail="Only PDF files allowed")

        content = await file.read()
        if len(content) > FREE_TIER_MAX_SIZE:
            raise HTTPException(413, detail="Free tier max 50 MB")

        if current_user.ocr_quota_remaining <= 0:
            raise HTTPException(403, detail="Insufficient OCR quota")

        book_id = uuid.uuid4()
        book = Book(
            id=book_id,
            user_id=current_user.id,
            title=title or file.filename.replace(".pdf", ""),
            original_filename=file.filename,
            status=BookStatus.PENDING,
            original_pdf_url=(
                f"s3://{settings.AWS_S3_BUCKET}/uploads/"
                f"{current_user.id}/{book_id}/{file.filename}"
            ),
        )
        db.add(book)
        db.commit()

        s3_key = f"uploads/{current_user.id}/{book_id}/{file.filename}"
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        if not s3_storage.upload_file(tmp_path, s3_key, "application/pdf"):
            os.unlink(tmp_path)
            raise HTTPException(500, detail="S3 upload failed")

        os.unlink(tmp_path)

        task = process_pdf_task.delay(
            book_id=str(book_id), s3_pdf_key=s3_key, user_id=str(current_user.id)
        )

        return ProcessBookResponse(
            book_id=str(book_id),
            status="processing",
            task_id=task.id,
            message="Upload and processing started",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Direct upload failed: {e}")
        raise HTTPException(500, detail="Upload failed")
