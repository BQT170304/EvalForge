"""Tests for structlog configuration and trace-context injection."""

import logging

from opentelemetry.sdk.trace import TracerProvider

from evalforge.observability.logging import configure_structlog, inject_trace_context


def test_inject_trace_context_adds_ids_inside_a_span():
    provider = TracerProvider()
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("test-span"):
        event_dict = inject_trace_context(None, "info", {})

    assert "trace_id" in event_dict
    assert "span_id" in event_dict
    assert len(event_dict["trace_id"]) == 32
    assert len(event_dict["span_id"]) == 16


def test_inject_trace_context_no_op_outside_a_span():
    event_dict = inject_trace_context(None, "info", {"message": "hello"})

    assert "trace_id" not in event_dict
    assert event_dict == {"message": "hello"}


def test_configure_structlog_is_idempotent_on_root_handlers():
    configure_structlog()
    configure_structlog()

    root_logger = logging.getLogger()
    stdout_handlers = [
        h for h in root_logger.handlers if getattr(h, "name", None) == "evalforge.stdout"
    ]
    assert len(stdout_handlers) == 1
