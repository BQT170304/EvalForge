"""Celery worker tasks for asynchronous evaluation execution."""

import asyncio
from typing import Any

import structlog

from evalforge.engine.base import EvalTestCase
from evalforge.engine.orchestrator import EvaluationOrchestrator
from evalforge.tasks.celery_app import celery_app

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, name="evalforge.tasks.evaluation_tasks.run_async_evaluation")  # type: ignore[untyped-decorator]
def run_async_evaluation(
    self: Any,
    eval_id: str,
    test_case_dict: dict[str, Any],
    metric_names: list[str],
    thresholds: dict[str, float],
    parameters: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Execute evaluation asynchronously in a Celery worker."""
    logger.info("Starting async evaluation task", task_id=self.request.id, eval_id=eval_id)

    test_case = EvalTestCase(
        input=test_case_dict["input"],
        output=test_case_dict["output"],
        expected_output=test_case_dict.get("expected_output"),
        context=test_case_dict.get("context"),
        metadata=test_case_dict.get("metadata"),
    )

    orchestrator = EvaluationOrchestrator()
    config: dict[str, Any] = {}
    for m in metric_names:
        cfg = parameters.get(m, {}).copy()
        if m in thresholds:
            cfg["threshold"] = thresholds[m]
        config[m] = cfg

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(
            orchestrator.evaluate(test_case=test_case, metric_names=metric_names, config=config)
        )
    finally:
        loop.close()

    total_cost = sum(r.cost_usd for r in results)
    total_latency = sum(r.latency_ms for r in results)
    overall_passed = all(r.passed for r in results) if results else False
    avg_score = sum(r.score for r in results) / len(results) if results else 0.0

    return {
        "eval_id": eval_id,
        "overall_passed": overall_passed,
        "average_score": avg_score,
        "total_cost_usd": total_cost,
        "latency_ms": total_latency,
        "results": [
            {
                "metric_name": r.metric_name,
                "category": r.category.value if hasattr(r.category, "value") else str(r.category),
                "source": r.source.value if hasattr(r.source, "value") else str(r.source),
                "score": r.score,
                "passed": r.passed,
                "threshold": r.threshold,
                "reason": r.reason,
                "details": r.details,
                "cost_usd": r.cost_usd,
                "latency_ms": r.latency_ms,
            }
            for r in results
        ],
    }
