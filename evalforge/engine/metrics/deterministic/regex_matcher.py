"""Regex matcher metric."""

import re
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


@MetricRegistry.register("regex_matcher")
class RegexMatcher(EvalForgeMetric):
    """Matches the output against a list of regular expressions."""

    def __init__(
        self,
        patterns: list[str],
        match_mode: str = "all",
        name: str = "regex_matcher",
        threshold: float = 1.0,
    ):
        super().__init__(
            name=name,
            category=MetricCategory.DETERMINISTIC,
            source=MetricSource.BUILTIN,
            threshold=threshold,
        )
        self.patterns = patterns
        self.match_mode = match_mode.lower()
        if self.match_mode not in ("all", "any"):
            raise ValueError("match_mode must be 'all' or 'any'")
        self._compiled_patterns = [re.compile(p) for p in patterns]

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        score = 0.0
        details: dict[str, Any] = {}
        reason = ""

        try:
            output = test_case.output or ""
            matches = []
            failures = []

            for pattern, compiled in zip(self.patterns, self._compiled_patterns, strict=True):
                if compiled.search(output):
                    matches.append(pattern)
                else:
                    failures.append(pattern)

            details["matches"] = matches
            details["failures"] = failures

            if not self.patterns:
                score = 1.0
                reason = "No patterns provided."
            else:
                score = len(matches) / len(self.patterns)
                if self.match_mode == "all":
                    reason = f"Matched {len(matches)} out of {len(self.patterns)} patterns."
                elif self.match_mode == "any":
                    score = 1.0 if matches else 0.0
                    reason = "Matched at least one pattern." if matches else "Matched no patterns."
        except Exception as e:
            score = 0.0
            reason = f"Regex matching failed: {e!s}"
            logger.exception("Regex matching failed", error=str(e))
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
