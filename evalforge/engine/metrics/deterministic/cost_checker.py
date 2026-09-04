"""Cost checker metric."""

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


@MetricRegistry.register("cost_checker")
class CostChecker(EvalForgeMetric):
    """Checks if the execution cost of the test case is within a maximum limit."""

    def __init__(self, max_cost_usd: float, name: str = "cost_checker", threshold: float = 0.5):
        super().__init__(
            name=name,
            category=MetricCategory.DETERMINISTIC,
            source=MetricSource.BUILTIN,
            threshold=threshold,
        )
        self.max_cost_usd = max_cost_usd

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        score = 0.0
        reason = ""
        details: dict[str, Any] = {}

        try:
            actual = test_case.cost_usd or 0.0
            details["actual_cost_usd"] = actual
            details["max_cost_usd"] = self.max_cost_usd

            if self.max_cost_usd > 0:
                score = max(0.0, 1.0 - (actual / self.max_cost_usd))
            else:
                score = 0.0 if actual > 0 else 1.0

            # Clamp score
            score = min(1.0, max(0.0, score))

            reason = f"Cost was ${actual:.4f} (max ${self.max_cost_usd:.4f})."
        except Exception as e:
            score = 0.0
            reason = f"Cost checking failed: {e!s}"
            logger.exception("Cost checking failed", error=str(e))
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
