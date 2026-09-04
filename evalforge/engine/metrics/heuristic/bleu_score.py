"""BLEU score metric using NLTK."""

import time

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


@MetricRegistry.register("BLEUScore")
@MetricRegistry.register("bleu_score")
class BLEUScore(EvalForgeMetric):
    """
    Computes BLEU score between output and expected_output using NLTK.
    """

    name: str = "BLEUScore"
    category: MetricCategory = MetricCategory.HEURISTIC
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.5):
        """Initialize the BLEUScore metric."""
        super().__init__(threshold=threshold)

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        """Evaluate the BLEU score between output and expected_output."""
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
                details={},
                cost_usd=0.0,
                latency_ms=latency,
            )

        try:
            import nltk
            from nltk.tokenize import word_tokenize
            from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu

            try:
                # Ensure punkt is downloaded
                nltk.data.find("tokenizers/punkt")
                nltk.data.find("tokenizers/punkt_tab")
            except LookupError:
                logger.info("downloading_nltk_punkt")
                nltk.download("punkt", quiet=True)
                nltk.download("punkt_tab", quiet=True)

            # Tokenize strings
            try:
                reference = [word_tokenize(test_case.expected_output.lower())]
                candidate = word_tokenize(test_case.output.lower())
            except Exception:
                reference = [test_case.expected_output.lower().split()]
                candidate = test_case.output.lower().split()

            if test_case.output.strip().lower() == test_case.expected_output.strip().lower():
                score = 1.0
                details = {"bleu_1": 1.0, "bleu_2": 1.0, "bleu_3": 1.0, "bleu_4": 1.0}
            else:
                chencherry = SmoothingFunction()
                weights = {
                    "bleu_1": (1, 0, 0, 0),
                    "bleu_2": (0.5, 0.5, 0, 0),
                    "bleu_3": (0.33, 0.33, 0.33, 0),
                    "bleu_4": (0.25, 0.25, 0.25, 0.25),
                }

                details = {}
                for weight_name, w in weights.items():
                    details[weight_name] = float(
                        sentence_bleu(
                            reference, candidate, weights=w, smoothing_function=chencherry.method1
                        )
                    )
                score = details["bleu_4"]

            passed = score >= self.threshold
            reason = (
                f"BLEU-4 ({score:.2f}) meets threshold"
                if passed
                else f"BLEU-4 ({score:.2f}) below threshold ({self.threshold})"
            )

            latency = (time.time() - start_time) * 1000

            return MetricResult(
                metric_name=self.name,
                score=score,
                passed=passed,
                threshold=self.threshold,
                reason=reason,
                source=self.source,
                details=details,
                cost_usd=0.0,
                latency_ms=latency,
            )

        except ImportError as err:
            logger.error("nltk_not_installed")
            raise ImportError("Please install nltk to use BLEUScore.") from err
        except Exception as e:
            logger.exception("bleu_score_error", error=str(e))
            latency = (time.time() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason=f"Error computing BLEU score: {e!s}",
                source=self.source,
                details={},
                cost_usd=0.0,
                latency_ms=latency,
            )
