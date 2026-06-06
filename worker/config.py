"""
Celery worker configuration and beat schedule.
Defines periodic tasks and worker settings.
"""

from celery.schedules import crontab

# Celery Beat schedule for periodic tasks
CELERY_BEAT_SCHEDULE = {
    "cleanup-old-books": {
        "task": "cleanup_old_books",
        "schedule": crontab(hour=2, minute=0),  # Run daily at 2 AM
    },
    "reset-monthly-quotas": {
        "task": "reset_monthly_quotas",
        "schedule": crontab(
            day_of_month=1, hour=0, minute=0
        ),  # Run on 1st of month at midnight
    },
}

# Worker configuration
WORKER_CONFIG = {
    "concurrency": 4,  # Number of concurrent worker processes
    "prefetch_multiplier": 1,  # Process one task at a time (prevents memory issues)
    "max_tasks_per_child": 1000,  # Restart worker after 1000 tasks
    "time_limit": 3600,  # Hard limit: 1 hour
    "soft_time_limit": 3300,  # Soft limit: 55 minutes
}
