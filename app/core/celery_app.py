"""
Celery application initialization and configuration.
Handles async task queue setup with Redis broker.
"""

from celery import Celery
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    "flexiread",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task configuration
    task_track_started=True,  # Track when task starts
    task_time_limit=3600,  # Hard limit: 1 hour
    task_soft_time_limit=3300,  # Soft limit: 55 minutes (warning)
    task_acks_late=True,                  # Ack only after successful execution
    task_reject_on_worker_lost=True,       # Re-queue task if worker dies mid-way
    broker_transport_options={
        'visibility_timeout': 43200,      # 12 hours timeout to prevent duplicate tasks
    },
    result_expires=86400,                 # Auto-expire results in 24 hours to save memory
    # Worker configuration
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leak)
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,  # Use from settings
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_max_retries=3,
    task_default_retry_delay=60,  # Retry after 1 minute
)

# Try to import worker config if it exists
try:
    from worker.config import CELERY_BEAT_SCHEDULE, WORKER_CONFIG

    celery_app.conf.update(beat_schedule=CELERY_BEAT_SCHEDULE)
    celery_app.conf.update(WORKER_CONFIG)
    logger.info("Worker configuration loaded from worker.config")
except ImportError:
    logger.warning("worker.config not found, using default celery settings")

logger.info(f"Celery configured with broker: {settings.CELERY_BROKER_URL}")
