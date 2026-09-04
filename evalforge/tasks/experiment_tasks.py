"""Celery background tasks for long-running batch experiment evaluations."""

import asyncio
import uuid
from typing import Any

import structlog

from evalforge.db.session import get_session_factory
from evalforge.experiments.runner import ExperimentRunner
from evalforge.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="evalforge.tasks.evaluation_tasks.run_experiment_batch")  # type: ignore[untyped-decorator]
def run_experiment_batch(
    self: Any,
    experiment_id: str,
    system_prompt: str | None = None,
    concurrency: int = 5,
) -> dict[str, Any]:
    """Executes a full dataset evaluation experiment inside a Celery background worker."""
    logger.info(
        "Starting background experiment task", task_id=self.request.id, experiment_id=experiment_id
    )

    async def _execute() -> dict[str, Any]:
        factory = get_session_factory()
        async with factory() as session:
            runner = ExperimentRunner(session)
            exp = await runner.run_experiment(
                experiment_id=uuid.UUID(experiment_id),
                system_prompt=system_prompt,
                concurrency=concurrency,
            )
            await session.commit()
            return {
                "experiment_id": str(exp.id),
                "status": exp.status,
                "pass_rate": exp.pass_rate,
                "total_entries": exp.total_entries,
                "passed_entries": exp.passed_entries,
                "failed_entries": exp.failed_entries,
                "duration_seconds": exp.duration_seconds,
                "total_cost_usd": exp.total_cost_usd,
            }

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_execute())
    finally:
        loop.close()
