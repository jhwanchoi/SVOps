import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create Celery instance with conditional import
try:
    from celery import Celery

    celery_app = Celery(
        "svops",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
        include=[
            "app.application.tasks.workflow_tasks",
            "app.application.tasks.dag_chain_tasks",
            "app.application.tasks.notification_tasks"
        ],
    )
    CELERY_AVAILABLE = True
except ImportError:
    logger.warning("Celery not available - background tasks disabled")
    celery_app = None
    CELERY_AVAILABLE = False

# Configuration (only if Celery is available)
if CELERY_AVAILABLE and celery_app:
    celery_app.conf.update(
        # Task routing
        task_routes={
            "app.application.tasks.workflow_tasks.*": {"queue": "workflow_monitoring"},
            "app.application.tasks.dag_chain_tasks.*": {"queue": "dag_chain"},
            "app.application.tasks.notification_tasks.*": {"queue": "notifications"},
        },
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Worker settings
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        worker_max_tasks_per_child=1000,
        # Beat settings (for periodic tasks)
        beat_schedule={
            "monitor-active-workflows": {
                "task": "app.application.tasks.workflow_tasks.monitor_active_workflows",
                "schedule": 30.0,  # Run every 30 seconds
            },
            "cleanup-completed-workflows": {
                "task": "app.application.tasks.workflow_tasks.cleanup_completed_workflows",
                "schedule": 300.0,  # Run every 5 minutes
            },
        },
        beat_schedule_filename="celerybeat-schedule",
    )

    # Set default queue
    celery_app.conf.task_default_queue = "default"

# Configure logging (only if Celery is available)
if CELERY_AVAILABLE:
    try:
        from celery.signals import after_setup_logger

        @after_setup_logger.connect
        def setup_loggers(logger_instance, *args, **kwargs):
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

            # File handler
            file_handler = logging.FileHandler("celery.log")
            file_handler.setFormatter(formatter)
            logger_instance.addHandler(file_handler)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger_instance.addHandler(console_handler)

    except ImportError:
        # Fallback if signals are not available
        pass


if __name__ == "__main__" and CELERY_AVAILABLE and celery_app:
    celery_app.start()
