"""
Celery tasks for asynchronous PDF processing and OCR.
Handles memory management, progress tracking, and error resilience.
"""

import os
import tempfile
import logging
import redis
import json
from typing import Optional
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.models.book import Book, BookStatus
from app.utils.s3_storage import s3_storage
from app.utils.ocr_processor import process_pdf_file

logger = logging.getLogger(__name__)

# Redis client for progress tracking (separate from Celery broker)
redis_client = redis.from_url(settings.REDIS_URL)

# Progress update batch size (update DB every N pages)
PROGRESS_BATCH_SIZE = 20


def update_progress_redis(book_id: str, current_page: int, total_pages: int) -> None:
    """
    Update progress in Redis (fast, non-blocking).
    
    Args:
        book_id: Book ID
        current_page: Current page number
        total_pages: Total pages
    """
    try:
        progress_key = f"book_progress:{book_id}"
        progress_pct = int((current_page / total_pages) * 100) if total_pages > 0 else 0
        
        redis_client.set(
            progress_key,
            json.dumps({
                "current_page": current_page,
                "total_pages": total_pages,
                "progress_percentage": progress_pct
            }),
            ex=3600  # Expire after 1 hour
        )
    except Exception as e:
        logger.warning(f"Redis progress update failed: {e}")


def batch_update_db_progress(
    db: Session,
    book_id: str,
    current_page: int,
    total_pages: int
) -> None:
    """
    Update progress in database (batched to reduce I/O).
    
    Args:
        db: Database session
        book_id: Book ID
        current_page: Current page number
        total_pages: Total pages
    """
    try:
        book = db.query(Book).filter(Book.id == book_id).first()
        if book:
            book.update_progress(current_page, total_pages)
            db.commit()
            logger.debug(f"DB progress updated: {book_id} - {current_page}/{total_pages}")
    except Exception as e:
        logger.error(f"DB progress update failed: {e}")
        db.rollback()


def progress_callback_factory(book_id: str):
    """
    Create a progress callback function for PDF processor.
    
    Args:
        book_id: Book ID
        
    Returns:
        Callback function
    """
    pages_processed = 0
    
    def callback(current_page: int, total_pages: int) -> None:
        nonlocal pages_processed
        pages_processed = current_page
        
        # Always update Redis (fast)
        update_progress_redis(book_id, current_page, total_pages)
        
        # Batch update to database (every N pages)
        if current_page % PROGRESS_BATCH_SIZE == 0 or current_page == total_pages:
            db = SessionLocal()
            try:
                batch_update_db_progress(db, book_id, current_page, total_pages)
            finally:
                db.close()
    
    return callback


@celery_app.task(bind=True, name="process_pdf_task")
def process_pdf_task(self, book_id: str, s3_pdf_key: str, user_id: str) -> dict:
    """
    Main Celery task for PDF processing and OCR.
    
    This is the heart of the system. Handles:
    - S3 download with streaming
    - Page-by-page processing
    - Smart OCR decision
    - Progress tracking with batching
    - Memory management
    - Error resilience
    
    Args:
        book_id: Book ID
        s3_pdf_key: S3 key to PDF file
        user_id: User ID (for quota tracking)
        
    Returns:
        Task result dictionary
    """
    db = None
    local_pdf_path = None
    
    try:
        logger.info(f"Starting PDF processing: book_id={book_id}, s3_key={s3_pdf_key}")
        
        # Initialize database session
        db = SessionLocal()
        
        # Fetch book from database
        book = db.query(Book).filter(Book.id == book_id).first()
        if not book:
            raise ValueError(f"Book not found: {book_id}")
        
        # Mark as processing
        book.status = BookStatus.PROCESSING
        db.commit()
        
        # Step 1: Download PDF from S3 to temporary file
        logger.info(f"Downloading PDF from S3: {s3_pdf_key}")
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
            local_pdf_path = tmp_file.name
        
        if not s3_storage.download_file(s3_pdf_key, local_pdf_path):
            raise RuntimeError(f"Failed to download PDF from S3: {s3_pdf_key}")
        
        file_size_mb = os.path.getsize(local_pdf_path) / (1024 * 1024)
        logger.info(f"PDF downloaded: {file_size_mb:.2f} MB")
        
        # Step 2: Process PDF with progress callback
        logger.info("Starting PDF processing...")
        progress_callback = progress_callback_factory(book_id)
        
        result, error = process_pdf_file(local_pdf_path, progress_callback)
        
        if error:
            raise RuntimeError(f"PDF processing failed: {error}")
        
        # Step 3: Prepare final result
        pages_data = result.get("pages", [])
        summary = result.get("summary", {})
        
        # Calculate quota consumption (only OCR pages count)
        ocr_pages = summary.get("ocr_pages", 0)
        
        # Step 4: Upload processed content to S3
        logger.info(f"Uploading processed content to S3...")
        content_s3_key = f"processed/{user_id}/{book_id}/content.json"
        
        parsed_content_url = s3_storage.upload_json(result, content_s3_key)
        if not parsed_content_url:
            raise RuntimeError("Failed to upload processed content to S3")
        
        # Step 5: Update database with completion
        logger.info("Updating database with completion status...")
        book.mark_completed(parsed_content_url)
        book.total_pages = summary.get("total_pages", 0)
        book.processed_pages = book.total_pages
        
        # Update user quota
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.consume_quota(ocr_pages)
        
        db.commit()
        
        # Step 6: Cleanup
        logger.info("Cleaning up temporary files...")
        if local_pdf_path and os.path.exists(local_pdf_path):
            os.unlink(local_pdf_path)
        
        # Clear Redis progress key
        redis_client.delete(f"book_progress:{book_id}")
        
        logger.info(f"PDF processing completed successfully: {book_id}")
        
        return {
            "status": "success",
            "book_id": book_id,
            "total_pages": summary.get("total_pages", 0),
            "ocr_pages": ocr_pages,
            "direct_pages": summary.get("direct_extraction_pages", 0),
            "parsed_content_url": parsed_content_url,
        }
    
    except Exception as e:
        logger.error(f"PDF processing failed: {e}", exc_info=True)
        
        # Mark as failed in database
        if db:
            try:
                book = db.query(Book).filter(Book.id == book_id).first()
                if book:
                    book.mark_failed(str(e))
                    db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update book status: {db_error}")
                db.rollback()
        
        # Cleanup temporary file
        if local_pdf_path and os.path.exists(local_pdf_path):
            try:
                os.unlink(local_pdf_path)
            except Exception as cleanup_error:
                logger.warning(f"Failed to cleanup temp file: {cleanup_error}")
        
        # Re-raise for Celery retry logic
        raise
    
    finally:
        # Always close database session
        if db:
            db.close()


@celery_app.task(name="cleanup_old_books")
def cleanup_old_books():
    """
    Periodic task to cleanup old failed/pending books and their S3 files.
    Should be scheduled to run daily.
    """
    from datetime import datetime, timedelta
    
    db = SessionLocal()
    try:
        # Find books older than 7 days in failed/pending state
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        old_books = db.query(Book).filter(
            Book.created_at < cutoff_date,
            Book.status.in_([BookStatus.FAILED, BookStatus.PENDING])
        ).all()
        
        for book in old_books:
            try:
                # Delete from S3
                if book.original_pdf_url:
                    s3_storage.delete_file(book.original_pdf_url)
                if book.parsed_content_url:
                    s3_storage.delete_file(book.parsed_content_url)
                
                # Delete from database
                db.delete(book)
                logger.info(f"Cleaned up old book: {book.id}")
            except Exception as e:
                logger.error(f"Cleanup failed for book {book.id}: {e}")
        
        db.commit()
        logger.info(f"Cleanup task completed: {len(old_books)} books removed")
    
    except Exception as e:
        logger.error(f"Cleanup task failed: {e}")
        db.rollback()
    
    finally:
        db.close()


# Import User model for quota tracking
from app.models.user import User
