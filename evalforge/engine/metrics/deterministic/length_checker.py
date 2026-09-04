"""Length checker metric."""

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


@MetricRegistry.register("length_checker")
class LengthChecker(EvalForgeMetric):
    """Checks if the length of the test case output falls within a specified range."""

    def __init__(
        self,
        min_length: int | None = None,
        max_length: int | None = None,
        name: str = "length_checker",
        threshold: float = 1.0,
    ):
        super().__init__(
            name=name,
            category=MetricCategory.DETERMINISTIC,
            source=MetricSource.BUILTIN,
            threshold=threshold,
        )
        self.min_length = min_length
        self.max_length = max_length

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        score = 0.0
        reason = ""
        details: dict[str, Any] = {}

        try:
            output_len = len(test_case.output) if test_case.output else 0
            details["length"] = output_len
            details["min_length"] = self.min_length
            details["max_length"] = self.max_length

            is_valid = True
            if self.min_length is not None and output_len < self.min_length:
                is_valid = False
            if self.max_length is not None and output_len > self.max_length:
                is_valid = False

            if is_valid:
                score = 1.0
                reason = f"Output length ({output_len}) is within bounds."
            else:
                score = 0.0
                reason = f"Output length ({output_len}) is out of bounds."

        except Exception as e:
            score = 0.0
            reason = f"Length checking failed: {e!s}"
            logger.exception("Length checking failed", error=str(e))
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
