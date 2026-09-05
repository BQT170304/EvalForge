"""Celery task configuration for EvalForge."""

import os

from celery import Celery
from celery.signals import worker_process_init
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from evalforge.observability.logging import configure_structlog
from evalforge.observability.otel import configure_observability

REDIS_URL = os.getenv("EVALFORGE_REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "evalforge",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "evalforge.tasks.evaluation_tasks",
        "evalforge.tasks.experiment_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    task_routes={
        "evalforge.tasks.evaluation_tasks.run_async_evaluation": {"queue": "evaluations"},
        "evalforge.tasks.evaluation_tasks.run_experiment_batch": {"queue": "experiments"},
    },
)


@worker_process_init.connect(weak=False)  # type: ignore[untyped-decorator]
def _init_worker_observability(**kwargs: object) -> None:
    """Configures OTel + structlog inside each forked Celery worker process."""
    configure_structlog()
    configure_observability()
    CeleryInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
