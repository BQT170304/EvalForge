"""PII scanner metric."""

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

try:
    from presidio_analyzer import AnalyzerEngine

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False


@MetricRegistry.register("pii_scanner")
class PIIScanner(EvalForgeMetric):
    """Scans the test case output for Personally Identifiable Information (PII) using Microsoft Presidio."""

    def __init__(
        self, entities: list[str] | None = None, name: str = "pii_scanner", threshold: float = 1.0
    ):
        super().__init__(
            name=name,
            category=MetricCategory.DETERMINISTIC,
            source=MetricSource.BUILTIN,
            threshold=threshold,
        )
        self.entities = entities
        self._analyzer = None
        if PRESIDIO_AVAILABLE:
            self._analyzer = AnalyzerEngine()
        else:
            logger.warning("presidio_analyzer is not installed. PIIScanner will fail.")

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.perf_counter()
        score = 0.0
        reason = ""
        details: dict[str, Any] = {}

        try:
            if not PRESIDIO_AVAILABLE or not self._analyzer:
                raise ImportError("presidio-analyzer is required for PIIScanner.")

            output_text = test_case.output or ""

            # Use 'en' as default language for presidio
            results = self._analyzer.analyze(
                text=output_text, entities=self.entities, language="en"
            )

            detected_entities = [
                {"type": r.entity_type, "start": r.start, "end": r.end, "score": r.score}
                for r in results
            ]

            details["entities"] = detected_entities
            details["count"] = len(detected_entities)

            if not detected_entities:
                score = 1.0
                reason = "No PII detected in output."
            else:
                score = max(0.0, 1.0 - (len(detected_entities) * 0.2))
                reason = f"Detected {len(detected_entities)} PII entities."

        except Exception as e:
            score = 0.0
            reason = f"PII scanning failed: {e!s}"
            logger.exception("PII scanning failed", error=str(e))
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
