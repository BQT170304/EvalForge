"""Tests for the DeepEval / RAGAS wrapper layer.

No network and no real judge model: the third-party metric is faked so that the
mapping into MetricResult, and the registration of every wrapped name, are the
only things under test.
"""

from typing import Any

import pytest

from evalforge.engine.base import EvalTestCase, MetricCategory, MetricSource
from evalforge.engine.registry import MetricRegistry
from evalforge.engine.wrappers.deepeval_wrapper import DeepEvalMetricWrapper

# Names the README advertises; a missing one means an upstream import or a
# registration decorator silently stopped working.
WRAPPED_METRIC_NAMES = [
    "deepeval_faithfulness",
    "deepeval_answer_relevancy",
    "deepeval_hallucination",
    "deepeval_toxicity",
    "deepeval_bias",
    "deepeval_geval",
    "deepeval_summarization",
    "deepeval_tool_correctness",
    "ragas_context_recall",
    "ragas_context_precision",
    "ragas_answer_similarity",
    "ragas_answer_relevancy",
    "ragas_faithfulness",
    "ragas_context_entities_recall",
    "ragas_composite",
]


class _FakeDeepEvalMetric:
    """Stands in for a deepeval metric class: synchronous `measure`, no network."""

    def __init__(self, threshold: float = 0.5, **_: Any) -> None:
        self.threshold = threshold
        self.score: float | None = None
        self.reason: str | None = None

    def measure(self, test_case: Any) -> None:
        self.score = 0.83
        self.reason = "claims are supported by the context"

    def is_successful(self) -> bool:
        return (self.score or 0.0) >= self.threshold


class _ExplodingDeepEvalMetric(_FakeDeepEvalMetric):
    def measure(self, test_case: Any) -> None:
        raise ValueError("judge model unreachable")


@pytest.mark.parametrize("metric_name", WRAPPED_METRIC_NAMES)
def test_wrapped_metric_is_registered(metric_name: str):
    assert MetricRegistry.get(metric_name) is not None


@pytest.mark.asyncio
async def test_deepeval_wrapper_maps_score_and_reason():
    metric = DeepEvalMetricWrapper(
        _FakeDeepEvalMetric, "fake_faithfulness", MetricCategory.RAG, threshold=0.7
    )
    result = await metric.evaluate(
        EvalTestCase(input="q", output="a", context=["supporting context"])
    )

    assert result.metric_name == "fake_faithfulness"
    assert result.score == pytest.approx(0.83)
    assert result.passed is True
    assert result.threshold == pytest.approx(0.7)
    assert result.reason == "claims are supported by the context"
    assert result.category == MetricCategory.RAG
    assert result.source == MetricSource.DEEPEVAL


@pytest.mark.asyncio
async def test_deepeval_wrapper_below_threshold_fails():
    metric = DeepEvalMetricWrapper(
        _FakeDeepEvalMetric, "fake_strict", MetricCategory.RAG, threshold=0.9
    )
    result = await metric.evaluate(EvalTestCase(input="q", output="a"))
    assert result.passed is False


@pytest.mark.asyncio
async def test_deepeval_wrapper_surfaces_engine_failure():
    """The wrapper raises; the orchestrator is the layer that turns it into a result."""
    metric = DeepEvalMetricWrapper(_ExplodingDeepEvalMetric, "fake_broken", MetricCategory.RAG)
    with pytest.raises(RuntimeError, match="DeepEval metric evaluation failed"):
        await metric.evaluate(EvalTestCase(input="q", output="a"))
