import time
from typing import Any

from deepeval.metrics.ragas import (
    RAGASAnswerRelevancyMetric,
    RAGASContextualEntitiesRecall,
    RAGASContextualPrecisionMetric,
    RAGASContextualRecallMetric,
    RAGASFaithfulnessMetric,
    RagasMetric,
)
from deepeval.test_case import LLMTestCase

from ..base import EvalForgeMetric, EvalTestCase, MetricCategory, MetricResult, MetricSource
from ..registry import MetricRegistry


class RagasMetricWrapper(EvalForgeMetric):
    source = MetricSource.RAGAS

    def __init__(
        self,
        deepeval_ragas_class: type,
        name: str,
        category: MetricCategory,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.category = category
        self.deepeval_ragas_class = deepeval_ragas_class

        # Instantiate the underlying DeepEval Ragas metric
        threshold = kwargs.pop("threshold", self.threshold)
        self.metric_instance = self.deepeval_ragas_class(threshold=threshold, **kwargs)

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.time()

        # Transform EvalTestCase to DeepEval LLMTestCase
        deepeval_tc = LLMTestCase(
            input=test_case.input,
            actual_output=test_case.output,
            expected_output=test_case.expected_output,
            retrieval_context=test_case.context,
        )

        try:
            if hasattr(self.metric_instance, "a_measure"):
                await self.metric_instance.a_measure(deepeval_tc)
            else:
                self.metric_instance.measure(deepeval_tc)
        except Exception as e:
            raise RuntimeError(f"Ragas metric evaluation failed: {e}") from e

        latency_ms = (time.time() - start_time) * 1000
        cost_usd = getattr(self.metric_instance, "cost", 0.0) or 0.0

        return MetricResult(
            metric_name=self.name,
            score=float(self.metric_instance.score or 0.0),
            passed=bool(self.metric_instance.is_successful()),
            threshold=float(self.metric_instance.threshold or 0.0),
            reason=self.metric_instance.reason or "",
            source=self.source,
            category=self.category,
            details={},
            cost_usd=cost_usd,
            latency_ms=latency_ms,
        )


def wrap_ragas_metric(
    deepeval_ragas_class: type,
    metric_name: str,
    metric_category: MetricCategory,
    **default_kwargs: Any,
) -> type[RagasMetricWrapper]:
    class WrappedMetric(RagasMetricWrapper):
        name = metric_name
        category = metric_category

        def __init__(self, **kwargs: Any) -> None:
            merged_kwargs = {**default_kwargs, **kwargs}
            super().__init__(deepeval_ragas_class, metric_name, metric_category, **merged_kwargs)

    MetricRegistry.register(metric_name)(WrappedMetric)
    return WrappedMetric


# Concrete wrappers
ContextRecall = wrap_ragas_metric(
    RAGASContextualRecallMetric, "ragas_context_recall", MetricCategory.RAG
)
ContextPrecision = wrap_ragas_metric(
    RAGASContextualPrecisionMetric, "ragas_context_precision", MetricCategory.RAG
)
AnswerSimilarity = wrap_ragas_metric(
    RAGASAnswerRelevancyMetric, "ragas_answer_similarity", MetricCategory.RAG
)
AnswerRelevancy = wrap_ragas_metric(
    RAGASAnswerRelevancyMetric, "ragas_answer_relevancy", MetricCategory.RAG
)
Faithfulness = wrap_ragas_metric(RAGASFaithfulnessMetric, "ragas_faithfulness", MetricCategory.RAG)
ContextEntitiesRecall = wrap_ragas_metric(
    RAGASContextualEntitiesRecall, "ragas_context_entities_recall", MetricCategory.RAG
)
CompositeRagas = wrap_ragas_metric(RagasMetric, "ragas_composite", MetricCategory.RAG)
