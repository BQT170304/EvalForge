"""Latency checker metric."""

import time
from typing import Any

import structlog

from evalforge.engine.base import (
    EvalForgeMetric,
    EvalTestCase,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from evalforge.engine.registry import MetricRegistry

logger = structlog.get_logger(__name__)


@MetricRegistry.register("latency_checker")
class LatencyChecker(EvalForgeMetric):
    """Checks if the execution latency of the test case is within a maximum limit."""

    def __init__(
        self, max_latency_ms: float, name: str = "latency_checker", threshold: float = 0.5
    ):
        super().__init__(
            name=name,
            category=MetricCategory.DETERMINISTIC,
            source=MetricSource.BUILTIN,
            threshold=threshold,
        )
        self.max_latency_ms = max_latency_ms

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        score = 0.0
        reason = ""
        details: dict[str, Any] = {}

        try:
            actual = test_case.latency_ms or 0.0
            details["actual_latency_ms"] = actual
            details["max_latency_ms"] = self.max_latency_ms

            score = (
                max(0.0, 1.0 - (actual / self.max_latency_ms)) if self.max_latency_ms > 0 else 0.0
            )

            # Clamp score
            score = min(1.0, max(0.0, score))

            reason = f"Latency was {actual:.2f}ms (max {self.max_latency_ms}ms)."
        except Exception as e:
            score = 0.0
            reason = f"Latency checking failed: {e!s}"
            logger.exception("Latency checking failed", error=str(e))
            details["error"] = str(e)

        latency_ms = (time.perf_counter() - start_time) * 1000

        return MetricResult(
            metric_name=self.name,
            score=score,
            passed=score >= self.threshold,
            threshold=self.threshold,
            reason=reason,
            source=self.source,
            details=details,
            cost_usd=0.0,
            latency_ms=latency_ms,
        )
