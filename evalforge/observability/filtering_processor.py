"""Span processor that only forwards GenAI-attributed spans to its exporter.

Used to route LLM-generation spans (judge model calls, synthetic
generation — anything carrying a `gen_ai.system` attribute) to Langfuse,
without also sending every unrelated HTTP/DB/Celery span there.
"""

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

_GEN_AI_MARKER_ATTRIBUTE = "gen_ai.system"


class GenAISpanFilterProcessor(SpanProcessor):  # type: ignore[misc]
    """Wraps a `BatchSpanProcessor`, forwarding only GenAI-attributed spans."""

    def __init__(self, exporter: SpanExporter) -> None:
        self._inner = BatchSpanProcessor(exporter)

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        pass

    def on_end(self, span: ReadableSpan) -> None:
        if span.attributes is not None and _GEN_AI_MARKER_ATTRIBUTE in span.attributes:
            self._inner.on_end(span)

    def shutdown(self) -> None:
        self._inner.shutdown()

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return self._inner.force_flush(timeout_millis)  # type: ignore[no-any-return]
