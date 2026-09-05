"""Tests for LiteLLMClient GenAI span attributes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from evalforge.utils.llm_client import LiteLLMClient


def _fake_response() -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="hello"))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        model="gpt-4o",
    )


@pytest.fixture
def traced_exporter(monkeypatch):
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr("evalforge.utils.llm_client.tracer", provider.get_tracer("test"))
    return exporter


@pytest.mark.asyncio
async def test_complete_span_carries_gen_ai_attributes(traced_exporter):
    with (
        patch(
            "evalforge.utils.llm_client.acompletion", new=AsyncMock(return_value=_fake_response())
        ),
        patch("evalforge.utils.llm_client.completion_cost", return_value=0.001),
    ):
        client = LiteLLMClient(default_model="gpt-4o")
        content, _cost, tokens = await client.complete(messages=[{"role": "user", "content": "hi"}])

    assert content == "hello"
    assert tokens == 15

    spans = traced_exporter.get_finished_spans()
    assert len(spans) == 1
    attrs = spans[0].attributes
    assert attrs["gen_ai.system"] == "litellm"
    assert attrs["gen_ai.request.model"] == "gpt-4o"
    assert attrs["gen_ai.response.model"] == "gpt-4o"
    assert attrs["gen_ai.usage.input_tokens"] == 10
    assert attrs["gen_ai.usage.output_tokens"] == 5
    assert attrs["evalforge.cost_usd"] == 0.001
