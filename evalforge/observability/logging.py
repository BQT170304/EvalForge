"""Structlog configuration: JSON logs correlated with the active OTel span.

Routes through stdlib `logging` (via `ProcessorFormatter`) so any handler
attached to the root logger — including the OTel `LoggingHandler`
registered by `observability.otel.install` — receives the same records.
Manages only its own stdout handler (identified by name), so it can be
called in any order relative to `observability.otel.configure_observability`
without clobbering that handler.
"""

import logging
import sys
from typing import Any

import structlog
from opentelemetry import trace

_STDOUT_HANDLER_NAME = "evalforge.stdout"


def inject_trace_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Structlog processor: adds trace_id/span_id when called inside a span."""
    span_context = trace.get_current_span().get_span_context()
    if span_context.is_valid:
        event_dict["trace_id"] = format(span_context.trace_id, "032x")
        event_dict["span_id"] = format(span_context.span_id, "016x")
    return event_dict


def configure_structlog(json_logs: bool = True) -> None:
    """Configures structlog to emit JSON (or console) logs to stdout."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        inject_trace_context,
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer = structlog.processors.JSONRenderer() if json_logs else structlog.dev.ConsoleRenderer()
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.name = _STDOUT_HANDLER_NAME

    root_logger = logging.getLogger()
    root_logger.handlers = [
        h for h in root_logger.handlers if getattr(h, "name", None) != _STDOUT_HANDLER_NAME
    ]
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
