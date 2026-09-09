"""Tests for GenAISpanFilterProcessor — only forwards gen_ai spans."""

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from evalforge.observability.filtering_processor import GenAISpanFilterProcessor


def test_forwards_only_spans_with_gen_ai_system_attribute():
    exporter = InMemorySpanExporter()
    processor = GenAISpanFilterProcessor(exporter)

    provider = TracerProvider()
    provider.add_span_processor(processor)
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("llm_call", attributes={"gen_ai.system": "litellm"}):
        pass
    with tracer.start_as_current_span("http_request", attributes={"http.method": "GET"}):
        pass

    processor.force_flush()

    exported_names = [span.name for span in exporter.get_finished_spans()]
    assert exported_names == ["llm_call"]


def test_shutdown_and_force_flush_delegate_to_inner_processor():
    exporter = InMemorySpanExporter()
    processor = GenAISpanFilterProcessor(exporter)

    assert processor.force_flush(timeout_millis=1000) is True
    processor.shutdown()
