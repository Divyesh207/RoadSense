import logging
import os

from celery import Celery
from celery.signals import worker_ready

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "road_ai_worker",
    broker=broker_url,
    backend=result_backend,
    include=["worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
)


@worker_ready.connect
def _log_inference_mode(**_kwargs) -> None:
    """Make the active inference mode (trained YOLO vs. OpenCV fallback) visible at startup."""
    from inference.model_registry import ModelRegistry

    logging.getLogger(__name__).warning("AI inference status: %s", ModelRegistry().inference_status())
