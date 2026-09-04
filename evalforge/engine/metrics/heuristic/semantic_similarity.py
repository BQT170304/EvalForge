"""Semantic similarity metric using sentence-transformers."""

import time
from typing import Any

import numpy as np
import structlog
from numpy.linalg import norm

from evalforge.engine.base import (
    EvalForgeMetric,
    EvalTestCase,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from evalforge.engine.registry import MetricRegistry

logger = structlog.get_logger(__name__)


@MetricRegistry.register("SemanticSimilarity")
@MetricRegistry.register("semantic_similarity")
class SemanticSimilarity(EvalForgeMetric):
    """
    Computes cosine similarity between output and expected_output embeddings.
    """

    name: str = "SemanticSimilarity"
    category: MetricCategory = MetricCategory.HEURISTIC
    source: MetricSource = MetricSource.CUSTOM
    version: str = "1.0.0"

    def __init__(self, threshold: float = 0.7, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize the SemanticSimilarity metric."""
        super().__init__(threshold=threshold)
        self.model_name = model_name
        self._model = None

    def _load_model(self) -> Any:
        """Lazy load the sentence-transformers model."""
        if self._model is None:
            logger.info("loading_sentence_transformers_model", model_name=self.model_name)
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except ImportError as err:
                logger.error("sentence_transformers_not_installed")
                raise ImportError(
                    "Please install sentence-transformers to use SemanticSimilarity."
                ) from err
        return self._model

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        """Evaluate the semantic similarity between output and expected_output."""
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
                details={"model": self.model_name},
                cost_usd=0.0,
                latency_ms=latency,
            )

        model = self._load_model()

        try:
            embeddings = model.encode([test_case.output, test_case.expected_output])
            vec1 = embeddings[0]
            vec2 = embeddings[1]

            # Compute cosine similarity
            similarity = float(np.dot(vec1, vec2) / (norm(vec1) * norm(vec2)))

            # Ensure similarity is within [0, 1]
            similarity = max(0.0, min(1.0, similarity))

            passed = similarity >= self.threshold
            reason = (
                f"Similarity ({similarity:.2f}) meets threshold"
                if passed
                else f"Similarity ({similarity:.2f}) below threshold ({self.threshold})"
            )

            latency = (time.time() - start_time) * 1000

            return MetricResult(
                metric_name=self.name,
                score=similarity,
                passed=passed,
                threshold=self.threshold,
                reason=reason,
                source=self.source,
                details={
                    "model": self.model_name,
                    "embedding_dimension": len(vec1),
                },
                cost_usd=0.0,
                latency_ms=latency,
            )

        except Exception as e:
            logger.exception("semantic_similarity_error", error=str(e))
            latency = (time.time() - start_time) * 1000
            return MetricResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.threshold,
                reason=f"Error computing similarity: {e!s}",
                source=self.source,
                details={"model": self.model_name},
                cost_usd=0.0,
                latency_ms=latency,
            )
