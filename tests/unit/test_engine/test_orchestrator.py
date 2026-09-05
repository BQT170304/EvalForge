"""Tests for EvaluationOrchestrator tracing and metrics wiring."""

from unittest.mock import AsyncMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

from evalforge.engine.base import EvalTestCase, MetricCategory, MetricResult, MetricSource
from evalforge.engine.orchestrator import EvaluationOrchestrator


@pytest.fixture
def traced_orchestrator(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr("evalforge.engine.orchestrator.tracer", provider.get_tracer("test"))
    return exporter


@pytest.mark.asyncio
async def test_evaluate_creates_a_span_per_metric(traced_orchestrator):
    fake_result = MetricResult(
        metric_name="length_checker",
        score=1.0,
        passed=True,
        threshold=0.5,
        reason="ok",
        source=MetricSource.BUILTIN,
        category=MetricCategory.DETERMINISTIC,
    )
    test_case = EvalTestCase(input="hi", output="hello")

    with patch("evalforge.engine.orchestrator.MetricRegistry.create") as mock_create:
        mock_metric = AsyncMock()
        mock_metric.evaluate.return_value = fake_result
        mock_metric.name = "length_checker"
        mock_create.return_value = mock_metric

        orchestrator = EvaluationOrchestrator()
        results = await orchestrator.evaluate(test_case=test_case, metrics=["length_checker"])

    assert results == [fake_result]
    span_names = [span.name for span in traced_orchestrator.get_finished_spans()]
    assert "evalforge.metric.evaluate" in span_names


@pytest.mark.asyncio
async def test_evaluate_records_exception_on_span_when_metric_fails(traced_orchestrator):
    test_case = EvalTestCase(input="hi", output="hello")

    with patch("evalforge.engine.orchestrator.MetricRegistry.create") as mock_create:
        mock_metric = AsyncMock()
        mock_metric.evaluate.side_effect = RuntimeError("boom")
        mock_metric.name = "length_checker"
        mock_metric.threshold = 0.5
        mock_metric.source = MetricSource.BUILTIN
        mock_metric.category = MetricCategory.DETERMINISTIC
        mock_create.return_value = mock_metric

        orchestrator = EvaluationOrchestrator()
        results = await orchestrator.evaluate(test_case=test_case, metrics=["length_checker"])

    assert len(results) == 1
    assert results[0].passed is False
    assert "boom" in results[0].reason

    finished_spans = traced_orchestrator.get_finished_spans()
    assert len(finished_spans) == 1
    assert len(finished_spans[0].events) == 1
    assert finished_spans[0].events[0].name == "exception"
    assert finished_spans[0].status.status_code == StatusCode.ERROR
