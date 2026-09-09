from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "sweety",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.workers.heartbeat"],
)

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    beat_schedule={
        "scan-due-heartbeats": {
            "task": "app.workers.heartbeat.scan_due_heartbeats",
            "schedule": settings.heartbeat_scan_seconds,
        }
    },
)

# crontab imported so beat can be extended later without another import cycle
_ = crontab
