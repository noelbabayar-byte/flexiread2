"""
Celery tasks for asynchronous PDF processing and OCR.
Handles memory management, progress tracking, and error resilience.
"""

import os
import tempfile
import logging
import json
from contextlib import contextmanager
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.core.config import settings
from app.core.redis_client import redis_manager
from app.models.book import Book, BookStatus
from app.models.user import User
from app.utils.s3_storage import s3_storage
from app.utils.ocr_processor import process_pdf_file

logger = logging.getLogger(__name__)

# Progress update batch size (update DB every N pages)
PROGRESS_BATCH_SIZE = 20


@contextmanager
def get_task_db():
    """Provide a transactional scope around a series of operations."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


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

        redis_manager.redis.set(
            progress_key,
            json.dumps(
                {
                    "current_page": current_page,
                    "total_pages": total_pages,
                    "progress_percentage": progress_pct,
                }
            ),
            ex=3600,  # Expire after 1 hour
        )
    except Exception as e:
        logger.warning(f"Redis progress update failed: {e}")


def batch_update_db_progress(
    db: Session, book_id: str, current_page: int, total_pages: int
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
            logger.debug(
                f"DB progress updated: {book_id} - {current_page}/{total_pages}"
            )
    except Exception as e:
        logger.error(f"DB progress update failed: {e}")
        db.rollback()


def progress_callback_factory(book_id: str, db_session: Session):
    """
    Create a progress callback function for PDF processor.

    Args:
        book_id: Book ID
        db_session: Database session to use for updates

    Returns:
        Callback function
    """

    def callback(current_page: int, total_pages: int) -> None:
        # Always update Redis (fast)
        update_progress_redis(book_id, current_page, total_pages)

        # Batch update to database (every N pages)
        if current_page % PROGRESS_BATCH_SIZE == 0 or current_page == total_pages:
            batch_update_db_progress(db_session, book_id, current_page, total_pages)

    return callback


@celery_app.task(
    name="process_pdf_task", bind=True, max_retries=3, default_retry_delay=60
)
def process_pdf_task(self, book_id: str, s3_pdf_key: str, user_id: str) -> dict:
    """
    Main Celery task for PDF processing and OCR.
    Uses Unit of Work pattern for session management and Smart Retry strategy.
    """
    local_pdf_path = None
    parsed_content_url = None
    content_s3_key = None

    with get_task_db() as db:
        try:
            logger.info(
                f"Starting PDF processing: book_id={book_id}, attempt={self.request.retries}"
            )

            # Fetch book from database
            book = db.query(Book).filter(Book.id == book_id).first()
            if not book:
                raise ValueError(f"Book not found: {book_id}")

            # Mark as processing (Reset status on each retry)
            book.status = BookStatus.PROCESSING
            db.commit()

            # Step 1: Download PDF from S3 to temporary file
            logger.info(f"Downloading PDF from S3: {s3_pdf_key}")
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
                local_pdf_path = tmp_file.name

            if not s3_storage.download_file(s3_pdf_key, local_pdf_path):
                raise RuntimeError(f"Failed to download PDF from S3: {s3_pdf_key}")

            # Step 2: Process PDF with progress callback (using existing db session)
            logger.info("Starting PDF processing...")
            progress_callback = progress_callback_factory(book_id, db)
            result, error = process_pdf_file(local_pdf_path, progress_callback)

            if error:
                raise RuntimeError(f"PDF processing failed: {error}")

            # Step 3: Prepare final result
            summary = result.get("summary", {})
            ocr_pages = summary.get("ocr_pages", 0)

            # Step 4: Upload processed content to S3
            logger.info("Uploading processed content to S3...")
            content_s3_key = f"processed/{user_id}/{book_id}/content.json"
            parsed_content_url = s3_storage.upload_json(result, content_s3_key)

            if not parsed_content_url:
                raise RuntimeError("Failed to upload processed content to S3")

            # Step 5: Update database with completion (Unit of Work)
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
            if local_pdf_path and os.path.exists(local_pdf_path):
                os.unlink(local_pdf_path)

            # Clear Redis progress key via RedisManager
            redis_manager.redis.delete(f"book_progress:{book_id}")

            logger.info(f"PDF processing completed successfully: {book_id}")

            return {
                "status": "success",
                "book_id": book_id,
                "total_pages": summary.get("total_pages", 0),
                "ocr_pages": ocr_pages,
                "parsed_content_url": parsed_content_url,
            }

        except Exception as e:
            # S3 compensating action
            if parsed_content_url and content_s3_key:
                try:
                    s3_storage.delete_file(content_s3_key)
                    logger.info(f"S3 cleanup successful: {content_s3_key}")
                except Exception as s3_err:
                    logger.error(f"S3 cleanup failed: {s3_err}")

            # Temp file cleanup
            if local_pdf_path and os.path.exists(local_pdf_path):
                try:
                    os.unlink(local_pdf_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to cleanup temp file: {cleanup_error}")

            # Smart Retry: Only mark as FAILED if max retries reached
            if self.request.retries >= self.max_retries:
                logger.critical(
                    f"Max retries reached for book {book_id}. Marking as FAILED."
                )
                try:
                    failed_book = db.query(Book).filter(Book.id == book_id).first()
                    if failed_book:
                        failed_book.mark_failed(str(e))
                        db.commit()
                except Exception as db_err:
                    logger.error(f"Could not mark book as failed: {db_err}")
                raise e
            else:
                # Still have retries left! Don't mark as failed, just retry
                raise self.retry(exc=e)


@celery_app.task(name="cleanup_old_books")
def cleanup_old_books():
    """
    Periodic task to cleanup old failed/pending books and their S3 files.
    Should be scheduled to run daily.
    """
    from datetime import datetime, timezone, timedelta

    with get_task_db() as db:
        try:
            # Find books older than 7 days in failed/pending state
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)

            old_books = (
                db.query(Book)
                .filter(
                    Book.created_at < cutoff_date,
                    Book.status.in_([BookStatus.FAILED, BookStatus.PENDING]),
                )
                .all()
            )

            for book in old_books:
                try:
                    # Delete from S3
                    if book.original_pdf_url:
                        s3_key = book.original_pdf_url.replace(
                            f"s3://{settings.AWS_S3_BUCKET}/", ""
                        )
                        s3_storage.delete_file(s3_key)
                    if book.parsed_content_url:
                        s3_key = book.parsed_content_url.replace(
                            f"s3://{settings.AWS_S3_BUCKET}/", ""
                        )
                        s3_storage.delete_file(s3_key)

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


@celery_app.task(name="reset_monthly_quotas")
def reset_monthly_quotas():
    """
    Periodic task to reset monthly quotas for all users.
    Should be scheduled to run on the 1st of each month.
    """
    with get_task_db() as db:
        try:
            users = db.query(User).all()
            now = datetime.now(timezone.utc)

            for user in users:
                # Reset based on subscription tier
                if user.plan_type.value == "pro":
                    user.ocr_quota_remaining = settings.PRO_TIER_MONTHLY_QUOTA
                else:
                    user.ocr_quota_remaining = settings.FREE_TIER_MONTHLY_QUOTA

                user.ocr_quota_reset_date = datetime(
                    now.year, now.month, 1, tzinfo=timezone.utc
                )

            db.commit()
            logger.info(f"Reset quotas for {len(users)} users")

            return {"status": "success", "users_reset": len(users)}

        except Exception as e:
            logger.error(f"Quota reset failed: {e}")
            db.rollback()
            raise
