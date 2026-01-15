"""
Celery application configuration.
"""

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "pixiserve",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.workers.tasks.thumbnails",
        "app.workers.tasks.exif",
        "app.workers.tasks.geocoding",
        "app.workers.tasks.ml_pipeline",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Worker settings
    worker_prefetch_multiplier=1,  # One task at a time for ML tasks
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks to prevent memory leaks

    # Task routing
    task_routes={
        "app.workers.tasks.thumbnails.*": {"queue": "thumbnails"},
        "app.workers.tasks.exif.*": {"queue": "default"},
        "app.workers.tasks.geocoding.*": {"queue": "default"},
        "app.workers.tasks.ml_pipeline.*": {"queue": "ml"},
    },

    # Task result settings
    result_expires=3600,  # Results expire after 1 hour

    # Rate limiting
    task_annotations={
        "app.workers.tasks.geocoding.reverse_geocode": {
            "rate_limit": "1/s",  # Respect geocoding API limits
        },
    },
)


# Task priority queues
celery_app.conf.task_queues = {
    "default": {
        "exchange": "default",
        "routing_key": "default",
    },
    "thumbnails": {
        "exchange": "thumbnails",
        "routing_key": "thumbnails",
    },
    "ml": {
        "exchange": "ml",
        "routing_key": "ml",
    },
}
