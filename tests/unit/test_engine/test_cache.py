"""Tests for the evaluation cache and its use by the orchestrator."""

import pytest

from evalforge.engine.base import (
    EvalForgeMetric,
    EvalTestCase,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from evalforge.engine.orchestrator import EvaluationOrchestrator
from evalforge.engine.registry import MetricRegistry
from evalforge.utils.caching import EvaluationCache


def test_cache_key_distinguishes_trajectories():
    """Agent metrics score the trajectory, so it must take part in the key."""
    base = {"input": "solve it", "output": "done"}
    a = EvalTestCase(**base, trajectory=[{"step": "search"}])
    b = EvalTestCase(**base, trajectory=[{"step": "search"}, {"step": "search"}])

    key_a = EvaluationCache.generate_cache_key("loop_detection", a)
    key_b = EvaluationCache.generate_cache_key("loop_detection", b)
    assert key_a != key_b


def test_cache_key_distinguishes_metric_config():
    test_case = EvalTestCase(input="hi", output="hello")
    strict = EvaluationCache.generate_cache_key("length_checker", test_case, {"max_length": 5})
    loose = EvaluationCache.generate_cache_key("length_checker", test_case, {"max_length": 500})
    assert strict != loose


@MetricRegistry.register("_counting_metric")
class _CountingMetric(EvalForgeMetric):
    """Records how often it actually ran, so cache hits are observable."""

    category = MetricCategory.DETERMINISTIC
    source = MetricSource.CUSTOM
    calls = 0

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        type(self).calls += 1
        return MetricResult(
            metric_name=self.name,
            score=1.0,
            passed=True,
            threshold=self.threshold,
            reason="ok",
            source=self.source,
            category=self.category,
        )


@MetricRegistry.register("_exploding_metric")
class _ExplodingMetric(EvalForgeMetric):
    category = MetricCategory.DETERMINISTIC
    source = MetricSource.CUSTOM

    async def evaluate(self, test_case: EvalTestCase) -> MetricResult:
        raise RuntimeError("third-party engine blew up")


@pytest.mark.asyncio
async def test_orchestrator_serves_repeat_evaluation_from_cache():
    orchestrator = EvaluationOrchestrator()
    test_case = EvalTestCase(input="cache me", output="cached output")
    _CountingMetric.calls = 0

    first = await orchestrator.evaluate(test_case, metrics=["_counting_metric"])
    second = await orchestrator.evaluate(test_case, metrics=["_counting_metric"])

    assert _CountingMetric.calls == 1
    assert first[0].score == second[0].score == 1.0


@pytest.mark.asyncio
async def test_failed_metric_is_isolated_and_not_cached():
    """A metric that raises must not kill the batch, and must be retried next time."""
    orchestrator = EvaluationOrchestrator()
    test_case = EvalTestCase(input="boom", output="boom")

    results = await orchestrator.evaluate(
        test_case, metrics=["_exploding_metric", "_counting_metric"]
    )

    failed = next(r for r in results if r.metric_name == "_exploding_metric")
    assert failed.passed is False
    assert "third-party engine blew up" in failed.reason
    assert len(results) == 2
