"""ROUGE score metric using rouge-score library."""

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


@MetricRegistry.register("ROUGEScore")
@MetricRegistry.register("rouge_score")
class ROUGEScore(EvalForgeMetric):
    """
    Computes ROUGE scores between output and expected_output.
    """

    name: str = "ROUGEScore"
    category: MetricCategory = MetricCategory.HEURISTIC
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.5, variant: str = "rougeL"):
        """Initialize the ROUGEScore metric.

        Args:
            threshold: Minimum score to pass.
            variant: The ROUGE variant to use for the main score ('rouge1', 'rouge2', 'rougeL').
        """
        super().__init__(threshold=threshold)
        self.variant = variant
        self.supported_variants = ["rouge1", "rouge2", "rougeL"]
        if self.variant not in self.supported_variants:
            logger.warning("invalid_rouge_variant", variant=self.variant, fallback="rougeL")
            self.variant = "rougeL"

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        """Evaluate the ROUGE score between output and expected_output."""
        start_time = time.time()

        if not test_case.expected_output:
            latency = (time.time() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason="Missing expected_output in test case",
                source=self.source,
                details={"variant": self.variant},
                cost_usd=0.0,
                latency_ms=latency,
            )

        try:
            from rouge_score import rouge_scorer

            scorer = rouge_scorer.RougeScorer(self.supported_variants, use_stemmer=True)
            scores = scorer.score(test_case.expected_output, test_case.output)

            details: dict[str, Any] = {"variant": self.variant}
            for v in self.supported_variants:
                details[f"{v}_precision"] = float(scores[v].precision)
                details[f"{v}_recall"] = float(scores[v].recall)
                details[f"{v}_fmeasure"] = float(scores[v].fmeasure)
                details[v] = {
                    "precision": float(scores[v].precision),
                    "recall": float(scores[v].recall),
                    "fmeasure": float(scores[v].fmeasure),
                }

            # The main score is the fmeasure of the selected variant
            main_score = float(details[f"{self.variant}_fmeasure"])

            passed = main_score >= self.threshold
            reason = (
                f"{self.variant} ({main_score:.2f}) meets threshold"
                if passed
                else f"{self.variant} ({main_score:.2f}) below threshold ({self.threshold})"
            )

            latency = (time.time() - start_time) * 1000

            return MetricResult(
                metric_name=self.name,
                score=main_score,
                passed=passed,
                threshold=self.threshold,
                reason=reason,
                source=self.source,
                details=details,
                cost_usd=0.0,
                latency_ms=latency,
            )

        except ImportError as err:
            logger.error("rouge_score_not_installed")
            raise ImportError("Please install rouge-score to use ROUGEScore.") from err
        except Exception as e:
            logger.exception("rouge_score_error", error=str(e))
            latency = (time.time() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason=f"Error computing ROUGE score: {e!s}",
                source=self.source,
                details={"variant": self.variant},
                cost_usd=0.0,
                latency_ms=latency,
            )
