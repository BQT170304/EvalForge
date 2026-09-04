import asyncio
import time
from typing import Any

import structlog

from .base import (
    EvalTestCase,
    EvaluationResponse,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from .registry import MetricRegistry

logger = structlog.get_logger(__name__)


class EvaluationOrchestrator:
    """Orchestrates parallel and batch evaluation of metrics across test cases."""

    async def evaluate(
        self,
        test_case: EvalTestCase,
        metrics: list[str] | None = None,
        metric_names: list[str] | None = None,
        thresholds: dict[str, float] | None = None,
        parameters: dict[str, dict[str, Any]] | None = None,
        config: dict[str, Any] | None = None,
    ) -> list[MetricResult]:
        """Evaluates a single test case across multiple metrics in parallel."""
        target_metrics = metrics or metric_names or []
        cfg_map: dict[str, Any] = (config or {}).copy()
        if parameters:
            cfg_map.update(parameters)

        resolved_metrics = []
        for name in target_metrics:
            m_kwargs = cfg_map.get(name, {}).copy()
            if thresholds and name in thresholds:
                m_kwargs["threshold"] = thresholds[name]
            try:
                resolved_metrics.append(MetricRegistry.create(name, **m_kwargs))
            except ValueError as e:
                logger.error("failed_to_load_metric", metric=name, error=str(e))

        async def run_metric(metric: Any) -> MetricResult:
            start_time = time.time()
            try:
                res: MetricResult = await metric.evaluate(test_case)
                return res
            except Exception as e:
                logger.error(
                    "metric_evaluation_failed",
                    metric=getattr(metric, "name", "unknown"),
                    error=str(e),
                )
                return MetricResult(
                    metric_name=getattr(metric, "name", "unknown"),
                    score=0.0,
                    passed=False,
                    threshold=getattr(metric, "threshold", 0.5),
                    reason=f"Evaluation failed: {e!s}",
                    source=getattr(metric, "source", MetricSource.BUILTIN),
                    category=getattr(metric, "category", MetricCategory.DETERMINISTIC),
                    latency_ms=(time.time() - start_time) * 1000,
                )

        results = await asyncio.gather(*(run_metric(m) for m in resolved_metrics))
        return list(results)

    async def evaluate_batch(
        self, test_cases: list[EvalTestCase], metric_names: list[str], config: dict[str, Any]
    ) -> EvaluationResponse:
        start_time = time.time()

        tasks = [
            self.evaluate(test_case=tc, metric_names=metric_names, config=config)
            for tc in test_cases
        ]
        batch_results = await asyncio.gather(*tasks)

        total_cost = 0.0

        formatted_results = []
        for results in batch_results:
            tc_results = []
            for r in results:
                total_cost += r.cost_usd
                tc_results.append(
                    {
                        "metric_name": r.metric_name,
                        "score": r.score,
                        "passed": r.passed,
                        "threshold": r.threshold,
                        "reason": r.reason,
                        "source": r.source.value,
                        "details": r.details,
                        "cost_usd": r.cost_usd,
                        "latency_ms": r.latency_ms,
                    }
                )
            formatted_results.append(tc_results)

        total_latency = (time.time() - start_time) * 1000

        # basic summary
        summary = {"total_test_cases": len(test_cases), "metrics_run": len(metric_names)}

        return EvaluationResponse(
            results=formatted_results,
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
            summary=summary,
        )
