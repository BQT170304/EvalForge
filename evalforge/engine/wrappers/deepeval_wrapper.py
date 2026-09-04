import time
from typing import Any

from deepeval.metrics import (
    AnswerRelevancyMetric,
    BiasMetric,
    FaithfulnessMetric,
    GEval,
    HallucinationMetric,
    SummarizationMetric,
    ToolCorrectnessMetric,
    ToxicityMetric,
)
from deepeval.test_case import LLMTestCase

from ..base import EvalForgeMetric, EvalTestCase, MetricCategory, MetricResult, MetricSource
from ..registry import MetricRegistry


class DeepEvalMetricWrapper(EvalForgeMetric):
    source = MetricSource.DEEPEVAL

    def __init__(
        self, deepeval_class: type, name: str, category: MetricCategory, **kwargs: Any
    ) -> None:
        super().__init__(**kwargs)
        self.name = name
        self.category = category
        self.deepeval_class = deepeval_class

        # Instantiate the underlying metric
        threshold = kwargs.pop("threshold", self.threshold)
        self.metric_instance = self.deepeval_class(threshold=threshold, **kwargs)

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        start_time = time.time()

        # Transform EvalTestCase to DeepEval LLMTestCase
        deepeval_tc = LLMTestCase(
            input=test_case.input,
            actual_output=test_case.output,
            expected_output=test_case.expected_output,
            retrieval_context=test_case.context,
            # tool_calls could be mapped if DeepEval schema allows
        )

        # DeepEval metrics run synchronously in most setups, but they do have an a_measure method
        try:
            if hasattr(self.metric_instance, "a_measure"):
                await self.metric_instance.a_measure(deepeval_tc)
            else:
                self.metric_instance.measure(deepeval_tc)
        except Exception as e:
            raise RuntimeError(f"DeepEval metric evaluation failed: {e}") from e

        latency_ms = (time.time() - start_time) * 1000

        # Not all metrics populate cost, just safety defaults
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


def wrap_deepeval_metric(
    deepeval_metric_class: type,
    metric_name: str,
    metric_category: MetricCategory,
    **default_kwargs: Any,
) -> type[DeepEvalMetricWrapper]:
    class WrappedMetric(DeepEvalMetricWrapper):
        name = metric_name
        category = metric_category

        def __init__(self, **kwargs: Any) -> None:
            merged_kwargs = {**default_kwargs, **kwargs}
            super().__init__(deepeval_metric_class, metric_name, metric_category, **merged_kwargs)

    # Register immediately
    MetricRegistry.register(metric_name)(WrappedMetric)
    return WrappedMetric


# Concrete wrappers
Faithfulness = wrap_deepeval_metric(FaithfulnessMetric, "deepeval_faithfulness", MetricCategory.RAG)
AnswerRelevancy = wrap_deepeval_metric(
    AnswerRelevancyMetric, "deepeval_answer_relevancy", MetricCategory.RAG
)
Hallucination = wrap_deepeval_metric(
    HallucinationMetric, "deepeval_hallucination", MetricCategory.LLM_JUDGE
)
Toxicity = wrap_deepeval_metric(ToxicityMetric, "deepeval_toxicity", MetricCategory.SAFETY)
Bias = wrap_deepeval_metric(BiasMetric, "deepeval_bias", MetricCategory.SAFETY)
GEvalMetric = wrap_deepeval_metric(GEval, "deepeval_geval", MetricCategory.LLM_JUDGE)
Summarization = wrap_deepeval_metric(
    SummarizationMetric, "deepeval_summarization", MetricCategory.LLM_JUDGE
)
ToolCorrectness = wrap_deepeval_metric(
    ToolCorrectnessMetric, "deepeval_tool_correctness", MetricCategory.AGENT
)
