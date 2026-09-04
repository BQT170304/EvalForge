"""BERTScore metric using bert-score library."""

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


@MetricRegistry.register("BERTScoreMetric")
@MetricRegistry.register("bert_score")
class BERTScoreMetric(EvalForgeMetric):
    """
    Computes BERTScore between output and expected_output.
    """

    name: str = "BERTScore"
    category: MetricCategory = MetricCategory.HEURISTIC
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.7, lang: str = "en"):
        """Initialize the BERTScoreMetric.

        Args:
            threshold: Minimum F1 score to pass.
            lang: Language for the underlying model.
        """
        super().__init__(threshold=threshold)
        self.lang = lang
        self._scorer = None

    def _load_model(self) -> Any:
        """Lazy load the BERTScore model."""
        if self._scorer is None:
            logger.info("loading_bert_score_model", lang=self.lang)
            try:
                from bert_score import BERTScorer

                self._scorer = BERTScorer(lang=self.lang, rescale_with_baseline=True)
            except ImportError as err:
                logger.error("bert_score_not_installed")
                raise ImportError("Please install bert-score to use BERTScoreMetric.") from err
        return self._scorer

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        """Evaluate the BERTScore between output and expected_output."""
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
                details={"lang": self.lang},
                cost_usd=0.0,
                latency_ms=latency,
            )

        try:
            scorer = self._load_model()

            p, r, f1 = scorer.score([test_case.output], [test_case.expected_output])

            precision = float(p.mean())
            recall = float(r.mean())
            f1_score = float(f1.mean())

            # Clamp to [0, 1] in case of rescaling issues
            f1_score = max(0.0, min(1.0, f1_score))

            passed = f1_score >= self.threshold
            reason = (
                f"BERTScore F1 ({f1_score:.2f}) meets threshold"
                if passed
                else f"BERTScore F1 ({f1_score:.2f}) below threshold ({self.threshold})"
            )

            latency = (time.time() - start_time) * 1000

            return MetricResult(
                metric_name=self.name,
                score=f1_score,
                passed=passed,
                threshold=self.threshold,
                reason=reason,
                source=self.source,
                details={
                    "precision": precision,
                    "recall": recall,
                    "f1": f1_score,
                    "model": scorer.model_type,
                    "lang": self.lang,
                },
                cost_usd=0.0,
                latency_ms=latency,
            )

        except Exception as e:
            logger.exception("bert_score_error", error=str(e))
            latency = (time.time() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason=f"Error computing BERTScore: {e!s}",
                source=self.source,
                details={"lang": self.lang},
                cost_usd=0.0,
                latency_ms=latency,
            )
