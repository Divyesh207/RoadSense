"""Celery producer used by the API to hand work to the AI worker.

The API never imports worker code: tasks are sent by name over the Redis
broker and executed by the `road_ai_worker` Celery app (services/ai-worker).
"""

import logging
import uuid
from functools import lru_cache

from celery import Celery
from kombu.exceptions import KombuError, OperationalError

from app.core.config import settings

logger = logging.getLogger(__name__)

PROCESS_INSPECTION_TASK = "tasks.process_inspection"


class TaskDispatchError(RuntimeError):
    """Raised when a task could not be handed to the message broker."""


@lru_cache(maxsize=1)
def get_celery_producer() -> Celery:
    # No result backend: job state is tracked in the processing_jobs table, and a
    # Redis result backend would block send_task while subscribing for results.
    producer = Celery("road_api_producer", broker=settings.CELERY_BROKER_URL)
    producer.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        # Fail fast inside a request instead of retrying the broker forever.
        broker_connection_timeout=3,
        broker_connection_retry_on_startup=False,
        broker_transport_options={"socket_connect_timeout": 2, "socket_timeout": 3},
        task_publish_retry=True,
        task_publish_retry_policy={
            "max_retries": 2,
            "interval_start": 0,
            "interval_step": 0.5,
            "interval_max": 1,
        },
    )
    return producer


def dispatch_inspection_processing(
    job_id: uuid.UUID,
    inspection_id: uuid.UUID,
    organization_id: uuid.UUID,
) -> str:
    """Publish the inspection processing task. The Celery task id is the job id,
    so a job maps to exactly one task message. Returns the task id."""
    try:
        result = get_celery_producer().send_task(
            PROCESS_INSPECTION_TASK,
            kwargs={
                "job_id": str(job_id),
                "inspection_id": str(inspection_id),
                "organization_id": str(organization_id),
            },
            task_id=str(job_id),
        )
    except (OperationalError, KombuError, OSError, TimeoutError) as exc:
        logger.error("Failed to dispatch %s for job %s: %s", PROCESS_INSPECTION_TASK, job_id, exc)
        raise TaskDispatchError(str(exc)) from exc
    return result.id
