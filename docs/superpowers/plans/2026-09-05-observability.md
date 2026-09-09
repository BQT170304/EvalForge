# Phase 3 Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Instrument EvalForge with OpenTelemetry (traces, metrics, logs), exporting everything to Grafana Cloud and LLM-generation spans to Langfuse, using one shared instrumentation layer.

**Architecture:** A new `evalforge/observability/` package builds and installs OTel `TracerProvider`/`MeterProvider`/`LoggerProvider` instances from settings (no-op when unset), plus a `structlog` configuration that injects trace/span IDs and bridges into stdlib `logging` so both stdout JSON and the OTel log exporter see the same records. Existing modules (`main.py`, `orchestrator.py`, `llm_client.py`, `celery_app.py`) get minimal edits to call into this package and add spans/metrics at the natural evaluation boundaries.

**Tech Stack:** `opentelemetry-api`/`sdk`/`exporter-otlp` (already a dependency), `opentelemetry-instrumentation-{fastapi,sqlalchemy,celery,redis}` (added in Task 1), `structlog` (already a dependency, currently unconfigured).

**Spec:** `docs/superpowers/specs/2026-09-05-observability-design.md`

## Global Constraints

- `uv run mypy evalforge` must stay clean (strict mode) after every task.
- `uv run ruff check --fix . && uv run ruff format .` must produce no remaining lint errors after every task.
- `uv run pytest tests/unit` must pass after every task — no regressions in the existing 25 tests.
- No real network calls to Grafana Cloud or Langfuse in any test — use `opentelemetry.sdk.trace.export.in_memory_span_exporter.InMemorySpanExporter` and construct real exporter objects only to inspect wiring, never to actually export.
- All new settings default to `""` (empty string) — observability must be fully opt-in; importing/starting the app with no credentials configured must not raise or attempt any network I/O.
- Follow existing patterns: `structlog.get_logger(__name__)` module-level loggers, dataclasses for internal DTOs, `EVALFORGE_`-prefixed env vars for new settings (matches `config.py`'s existing `env_prefix`).

---

### Task 1: Grafana Cloud config settings + env example

**Files:**
- Modify: `evalforge/config.py` (add 3 fields after the existing `--- OpenTelemetry ---` block, line 77)
- Modify: `.env.example` (add corresponding entries under `--- OpenTelemetry ---`)
- Test: `tests/unit/test_config.py` (new file)

**Interfaces:**
- Produces: `Settings.grafana_otlp_endpoint: str`, `Settings.grafana_otlp_instance_id: str`, `Settings.grafana_otlp_api_key: str` — all default `""`. Consumed by Task 4 (`observability/otel.py`).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_config.py`:

```python
"""Tests for observability-related settings additions."""

from evalforge.config import Settings


def test_grafana_otlp_settings_default_to_empty(monkeypatch):
    monkeypatch.delenv("EVALFORGE_GRAFANA_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("EVALFORGE_GRAFANA_OTLP_INSTANCE_ID", raising=False)
    monkeypatch.delenv("EVALFORGE_GRAFANA_OTLP_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.grafana_otlp_endpoint == ""
    assert settings.grafana_otlp_instance_id == ""
    assert settings.grafana_otlp_api_key == ""


def test_grafana_otlp_settings_read_from_env(monkeypatch):
    monkeypatch.setenv("EVALFORGE_GRAFANA_OTLP_ENDPOINT", "https://otlp-gateway-prod-xx.grafana.net/otlp")
    monkeypatch.setenv("EVALFORGE_GRAFANA_OTLP_INSTANCE_ID", "123456")
    monkeypatch.setenv("EVALFORGE_GRAFANA_OTLP_API_KEY", "glc_fake_token")

    settings = Settings(_env_file=None)

    assert settings.grafana_otlp_endpoint == "https://otlp-gateway-prod-xx.grafana.net/otlp"
    assert settings.grafana_otlp_instance_id == "123456"
    assert settings.grafana_otlp_api_key == "glc_fake_token"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'grafana_otlp_endpoint'`

- [ ] **Step 3: Add the settings fields**

In `evalforge/config.py`, immediately after line 77 (`otel_service_name: str = "evalforge"`), add:

```python
    grafana_otlp_endpoint: str = ""
    grafana_otlp_instance_id: str = ""
    grafana_otlp_api_key: str = ""
```

- [ ] **Step 4: Update `.env.example`**

In `.env.example`, under the existing `# --- OpenTelemetry ---` section, add:

```bash
# --- OpenTelemetry ---
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=evalforge

# Grafana Cloud (free tier) — see docs/observability-setup.md for how to get these
EVALFORGE_GRAFANA_OTLP_ENDPOINT=
EVALFORGE_GRAFANA_OTLP_INSTANCE_ID=
EVALFORGE_GRAFANA_OTLP_API_KEY=
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green, 27 tests passed (25 existing + 2 new)

- [ ] **Step 7: Commit**

```bash
git add evalforge/config.py .env.example tests/unit/test_config.py
git commit -m "feat(observability): add Grafana Cloud OTLP settings"
```

---

### Task 2: Observability metric instruments

**Files:**
- Create: `evalforge/observability/__init__.py` (empty)
- Create: `evalforge/observability/metrics.py`
- Test: `tests/unit/test_observability/__init__.py` (empty)
- Test: `tests/unit/test_observability/test_metrics.py`

**Interfaces:**
- Produces: `evalforge.observability.metrics.eval_requests_total` (Counter), `eval_latency_ms` (Histogram), `eval_cost_usd_total` (Counter), `metric_failures_total` (Counter) — all module-level singletons. Consumed by Task 7 (`orchestrator.py`).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_observability/test_metrics.py`:

```python
"""Tests for observability metric instrument definitions."""

from evalforge.observability import metrics


def test_instruments_record_without_raising():
    metrics.eval_requests_total.add(1, {"metric_name": "bleu"})
    metrics.eval_latency_ms.record(12.3, {"metric_name": "bleu"})
    metrics.eval_cost_usd_total.add(0.002, {"metric_name": "llm_judge"})
    metrics.metric_failures_total.add(1, {"metric_name": "rouge"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_observability/test_metrics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evalforge.observability'`

- [ ] **Step 3: Create the package and metrics module**

Create `evalforge/observability/__init__.py` (empty file).

Create `evalforge/observability/metrics.py`:

```python
"""OTel metric instruments shared across the evaluation pipeline.

Recording against these instruments is always safe: with no MeterProvider
configured (the default, see observability.otel), the OTel API returns a
no-op meter and every call below is a silent no-op.
"""

from opentelemetry import metrics

_meter = metrics.get_meter("evalforge.observability")

eval_requests_total = _meter.create_counter(
    name="evalforge.eval_requests_total",
    unit="1",
    description="Total number of metric evaluations executed",
)

eval_latency_ms = _meter.create_histogram(
    name="evalforge.eval_latency_ms",
    unit="ms",
    description="Latency of individual metric evaluations",
)

eval_cost_usd_total = _meter.create_counter(
    name="evalforge.eval_cost_usd_total",
    unit="usd",
    description="Cumulative cost in USD of LLM-based evaluations",
)

metric_failures_total = _meter.create_counter(
    name="evalforge.metric_failures_total",
    unit="1",
    description="Total number of metric evaluation failures",
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_observability/test_metrics.py -v`
Expected: PASS

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add evalforge/observability/__init__.py evalforge/observability/metrics.py tests/unit/test_observability/
git commit -m "feat(observability): add OTel metric instruments"
```

---

### Task 3: GenAI span-filtering processor (for Langfuse export)

**Files:**
- Create: `evalforge/observability/filtering_processor.py`
- Test: `tests/unit/test_observability/test_filtering_processor.py`

**Interfaces:**
- Consumes: nothing new (only `opentelemetry.sdk.trace`/`export` APIs).
- Produces: `evalforge.observability.filtering_processor.GenAISpanFilterProcessor(exporter: SpanExporter)` — a `SpanProcessor` subclass. Consumed by Task 4 (`observability/otel.py`).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_observability/test_filtering_processor.py`:

```python
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

    with tracer.start_as_current_span(
        "llm_call", attributes={"gen_ai.system": "litellm"}
    ):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_observability/test_filtering_processor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evalforge.observability.filtering_processor'`

- [ ] **Step 3: Implement the processor**

Create `evalforge/observability/filtering_processor.py`:

```python
"""Span processor that only forwards GenAI-attributed spans to its exporter.

Used to route LLM-generation spans (judge model calls, synthetic
generation — anything carrying a `gen_ai.system` attribute) to Langfuse,
without also sending every unrelated HTTP/DB/Celery span there.
"""

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter

_GEN_AI_MARKER_ATTRIBUTE = "gen_ai.system"


class GenAISpanFilterProcessor(SpanProcessor):
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
        return self._inner.force_flush(timeout_millis)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_observability/test_filtering_processor.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add evalforge/observability/filtering_processor.py tests/unit/test_observability/test_filtering_processor.py
git commit -m "feat(observability): add GenAI span filter for Langfuse export"
```

---

### Task 4: Provider construction — `observability/otel.py`

**Files:**
- Create: `evalforge/observability/otel.py`
- Test: `tests/unit/test_observability/test_otel.py`

**Interfaces:**
- Consumes: `evalforge.config.Settings` (Task 1 fields + existing `langfuse_public_key`/`langfuse_secret_key`/`langfuse_host`/`otel_service_name`), `evalforge.observability.filtering_processor.GenAISpanFilterProcessor` (Task 3).
- Produces: `ObservabilityProviders` dataclass (`tracer_provider`, `meter_provider`, `logger_provider`), `build_providers(settings: Settings) -> ObservabilityProviders`, `install(providers: ObservabilityProviders) -> None`, `configure_observability(settings: Settings | None = None) -> ObservabilityProviders`. Consumed by Task 6 (`main.py`) and Task 9 (`celery_app.py`).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_observability/test_otel.py`:

```python
"""Tests for OTel provider construction — no real network calls are made."""

from evalforge.config import Settings
from evalforge.observability.otel import build_providers


def _settings(**overrides: str) -> Settings:
    defaults: dict[str, str] = {
        "grafana_otlp_endpoint": "",
        "grafana_otlp_instance_id": "",
        "grafana_otlp_api_key": "",
        "langfuse_public_key": "",
        "langfuse_secret_key": "",
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


def _span_processor_count(providers) -> int:
    return len(providers.tracer_provider._active_span_processor._span_processors)


def _metric_reader_count(providers) -> int:
    return len(providers.meter_provider._metric_readers)


def _log_processor_count(providers) -> int:
    return len(
        providers.logger_provider._multi_log_record_processor._log_record_processors
    )


def test_no_destinations_configured_registers_nothing():
    providers = build_providers(_settings())

    assert _span_processor_count(providers) == 0
    assert _metric_reader_count(providers) == 0
    assert _log_processor_count(providers) == 0


def test_grafana_only_registers_trace_metric_and_log_pipelines():
    providers = build_providers(
        _settings(
            grafana_otlp_endpoint="https://otlp-gateway-prod-xx.grafana.net/otlp",
            grafana_otlp_instance_id="123456",
            grafana_otlp_api_key="glc_fake_token",
        )
    )

    assert _span_processor_count(providers) == 1
    assert _metric_reader_count(providers) == 1
    assert _log_processor_count(providers) == 1


def test_langfuse_only_registers_one_filtered_trace_processor():
    providers = build_providers(
        _settings(
            langfuse_public_key="pk-fake",
            langfuse_secret_key="sk-fake",
        )
    )

    assert _span_processor_count(providers) == 1
    assert _metric_reader_count(providers) == 0
    assert _log_processor_count(providers) == 0


def test_both_destinations_registers_two_trace_processors():
    providers = build_providers(
        _settings(
            grafana_otlp_endpoint="https://otlp-gateway-prod-xx.grafana.net/otlp",
            grafana_otlp_instance_id="123456",
            grafana_otlp_api_key="glc_fake_token",
            langfuse_public_key="pk-fake",
            langfuse_secret_key="sk-fake",
        )
    )

    assert _span_processor_count(providers) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_observability/test_otel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evalforge.observability.otel'`

- [ ] **Step 3: Implement `otel.py`**

Create `evalforge/observability/otel.py`:

```python
"""Builds and installs OpenTelemetry providers from application settings.

Each destination (Grafana Cloud, Langfuse) registers its exporters only
when its settings are populated — with nothing configured, the returned
providers hold zero processors/readers and every OTel API call in the app
becomes a no-op. No network I/O happens at import time or when settings
are empty.
"""

import base64
from dataclasses import dataclass

from opentelemetry import _logs as otel_logs
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from evalforge import __version__
from evalforge.config import Settings, get_settings
from evalforge.observability.filtering_processor import GenAISpanFilterProcessor


@dataclass
class ObservabilityProviders:
    """The three OTel providers configured for this process."""

    tracer_provider: TracerProvider
    meter_provider: MeterProvider
    logger_provider: LoggerProvider


def _basic_auth_header(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def build_providers(settings: Settings) -> ObservabilityProviders:
    """Builds tracer/meter/logger providers wired to whichever destinations are configured."""
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": __version__,
            "deployment.environment": settings.env.value,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    metric_readers: list[PeriodicExportingMetricReader] = []
    logger_provider = LoggerProvider(resource=resource)

    if settings.grafana_otlp_endpoint:
        grafana_headers = _basic_auth_header(
            settings.grafana_otlp_instance_id, settings.grafana_otlp_api_key
        )
        tracer_provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(
                    endpoint=f"{settings.grafana_otlp_endpoint}/v1/traces",
                    headers=grafana_headers,
                )
            )
        )
        metric_readers.append(
            PeriodicExportingMetricReader(
                OTLPMetricExporter(
                    endpoint=f"{settings.grafana_otlp_endpoint}/v1/metrics",
                    headers=grafana_headers,
                )
            )
        )
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=f"{settings.grafana_otlp_endpoint}/v1/logs",
                    headers=grafana_headers,
                )
            )
        )

    if settings.langfuse_public_key and settings.langfuse_secret_key:
        langfuse_headers = _basic_auth_header(
            settings.langfuse_public_key, settings.langfuse_secret_key
        )
        tracer_provider.add_span_processor(
            GenAISpanFilterProcessor(
                OTLPSpanExporter(
                    endpoint=f"{settings.langfuse_host}/api/public/otel/v1/traces",
                    headers=langfuse_headers,
                )
            )
        )

    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)

    return ObservabilityProviders(
        tracer_provider=tracer_provider,
        meter_provider=meter_provider,
        logger_provider=logger_provider,
    )


def install(providers: ObservabilityProviders) -> None:
    """Registers the given providers as the process-global OTel defaults.

    Also attaches an OTel `LoggingHandler` to the root stdlib logger so
    `structlog` output (bridged into stdlib logging by
    observability.logging.configure_structlog) reaches the log exporter too.
    """
    trace.set_tracer_provider(providers.tracer_provider)
    metrics.set_meter_provider(providers.meter_provider)
    otel_logs.set_logger_provider(providers.logger_provider)

    import logging

    otel_handler = LoggingHandler(logger_provider=providers.logger_provider)
    otel_handler.name = "evalforge.otel"
    root_logger = logging.getLogger()
    root_logger.handlers = [
        h for h in root_logger.handlers if getattr(h, "name", None) != "evalforge.otel"
    ]
    root_logger.addHandler(otel_handler)


def configure_observability(settings: Settings | None = None) -> ObservabilityProviders:
    """Builds and installs OTel providers from settings. Safe to call once per process."""
    resolved = settings or get_settings()
    providers = build_providers(resolved)
    install(providers)
    return providers
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_observability/test_otel.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green. If mypy complains about the private-attribute access in the test file, that's expected and fine — mypy strict applies to `evalforge/`, not `tests/`, per this project's existing `pyproject.toml` mypy config (`[tool.mypy]` targets the package, not tests).

- [ ] **Step 6: Commit**

```bash
git add evalforge/observability/otel.py tests/unit/test_observability/test_otel.py
git commit -m "feat(observability): build and install OTel providers for Grafana Cloud + Langfuse"
```

---

### Task 5: Structured logging — `observability/logging.py`

**Files:**
- Create: `evalforge/observability/logging.py`
- Test: `tests/unit/test_observability/test_logging.py`

**Interfaces:**
- Produces: `evalforge.observability.logging.configure_structlog(json_logs: bool = True) -> None`, `inject_trace_context(logger, method_name, event_dict) -> dict` (structlog processor, exported for direct testing). Consumed by Task 6 (`main.py`) and Task 9 (`celery_app.py`).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_observability/test_logging.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_observability/test_logging.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'evalforge.observability.logging'`

- [ ] **Step 3: Implement `logging.py`**

Create `evalforge/observability/logging.py`:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_observability/test_logging.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add evalforge/observability/logging.py tests/unit/test_observability/test_logging.py
git commit -m "feat(observability): configure structlog with OTel trace correlation"
```

---

### Task 6: Wire the API process — `main.py`

**Files:**
- Modify: `evalforge/main.py`
- Test: `tests/integration/test_api.py` (existing — must still pass; confirms instrumenting the app doesn't break request handling)

**Interfaces:**
- Consumes: `evalforge.observability.logging.configure_structlog` (Task 5), `evalforge.observability.otel.configure_observability` (Task 4).

- [ ] **Step 1: Run existing integration tests to confirm current baseline**

Run: `uv run pytest tests/integration/test_api.py tests/integration/test_phase2_api.py -v`
Expected: PASS (baseline, before this task's edits)

- [ ] **Step 2: Edit `main.py`**

In `evalforge/main.py`, replace lines 1-20 (imports through `logger = structlog.get_logger(__name__)`) with:

```python
"""FastAPI application entry point.

Creates and configures the FastAPI application with middleware,
exception handlers, and API routes.
"""

import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from evalforge import __version__
from evalforge.api.v1.router import api_v1_router
from evalforge.config import get_settings
from evalforge.observability.logging import configure_structlog
from evalforge.observability.otel import configure_observability

configure_structlog()
configure_observability()
SQLAlchemyInstrumentor().instrument()
RedisInstrumentor().instrument()

logger = structlog.get_logger(__name__)
```

Leave everything from `@asynccontextmanager` through `return app` unchanged.

At the bottom of the file, replace:

```python
# Application instance for uvicorn
app = create_app()
```

with:

```python
# Application instance for uvicorn
app = create_app()
FastAPIInstrumentor.instrument_app(app)
```

- [ ] **Step 3: Run existing integration tests to verify no regression**

Run: `uv run pytest tests/integration/test_api.py tests/integration/test_phase2_api.py -v`
Expected: PASS — same results as Step 1's baseline

- [ ] **Step 4: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 5: Commit**

```bash
git add evalforge/main.py
git commit -m "feat(observability): wire OTel + structlog into the API process"
```

---

### Task 7: Instrument `EvaluationOrchestrator`

**Files:**
- Modify: `evalforge/engine/orchestrator.py`
- Test: `tests/unit/test_engine/test_orchestrator.py` (new file)

**Interfaces:**
- Consumes: `evalforge.observability.metrics.{eval_requests_total, eval_latency_ms, eval_cost_usd_total, metric_failures_total}` (Task 2).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_engine/test_orchestrator.py`:

```python
"""Tests for EvaluationOrchestrator tracing and metrics wiring."""

from unittest.mock import AsyncMock, patch

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

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

    with patch(
        "evalforge.engine.orchestrator.MetricRegistry.create"
    ) as mock_create:
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

    with patch(
        "evalforge.engine.orchestrator.MetricRegistry.create"
    ) as mock_create:
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_engine/test_orchestrator.py -v`
Expected: FAIL — `AttributeError: <module 'evalforge.engine.orchestrator'> does not have the attribute 'tracer'`

- [ ] **Step 3: Instrument `orchestrator.py`**

In `evalforge/engine/orchestrator.py`, replace lines 1-16 with:

```python
import asyncio
import time
from typing import Any

import structlog
from opentelemetry import trace

from evalforge.observability.metrics import (
    eval_cost_usd_total,
    eval_latency_ms,
    eval_requests_total,
    metric_failures_total,
)

from .base import (
    EvalTestCase,
    EvaluationResponse,
    MetricCategory,
    MetricResult,
    MetricSource,
)
from .registry import MetricRegistry

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)
```

Replace the `run_metric` inner function (originally lines 47-67) with:

```python
        async def run_metric(metric: Any) -> MetricResult:
            metric_name = getattr(metric, "name", "unknown")
            start_time = time.time()
            with tracer.start_as_current_span(
                "evalforge.metric.evaluate",
                attributes={"evalforge.metric_name": metric_name},
            ) as span:
                try:
                    res: MetricResult = await metric.evaluate(test_case)
                    duration_ms = (time.time() - start_time) * 1000
                    eval_requests_total.add(1, {"metric_name": metric_name})
                    eval_latency_ms.record(duration_ms, {"metric_name": metric_name})
                    eval_cost_usd_total.add(res.cost_usd, {"metric_name": metric_name})
                    span.set_attribute("evalforge.score", res.score)
                    span.set_attribute("evalforge.passed", res.passed)
                    return res
                except Exception as e:
                    metric_failures_total.add(1, {"metric_name": metric_name})
                    span.record_exception(e)
                    logger.error(
                        "metric_evaluation_failed",
                        metric=metric_name,
                        error=str(e),
                    )
                    return MetricResult(
                        metric_name=metric_name,
                        score=0.0,
                        passed=False,
                        threshold=getattr(metric, "threshold", 0.5),
                        reason=f"Evaluation failed: {e!s}",
                        source=getattr(metric, "source", MetricSource.BUILTIN),
                        category=getattr(metric, "category", MetricCategory.DETERMINISTIC),
                        latency_ms=(time.time() - start_time) * 1000,
                    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_engine/test_orchestrator.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add evalforge/engine/orchestrator.py tests/unit/test_engine/test_orchestrator.py
git commit -m "feat(observability): add spans and metrics to EvaluationOrchestrator"
```

---

### Task 8: Instrument `LiteLLMClient` with GenAI span attributes

**Files:**
- Modify: `evalforge/utils/llm_client.py`
- Test: `tests/unit/test_utils/__init__.py` (new, empty)
- Test: `tests/unit/test_utils/test_llm_client.py` (new file)

**Interfaces:**
- Produces: spans named `evalforge.llm.complete` carrying `gen_ai.system`, `gen_ai.request.model`, `gen_ai.response.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `evalforge.cost_usd` — this is the attribute set `GenAISpanFilterProcessor` (Task 3) keys on.

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_utils/test_llm_client.py`:

```python
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
        patch("evalforge.utils.llm_client.acompletion", new=AsyncMock(return_value=_fake_response())),
        patch("evalforge.utils.llm_client.completion_cost", return_value=0.001),
    ):
        client = LiteLLMClient(default_model="gpt-4o")
        content, cost, tokens = await client.complete(messages=[{"role": "user", "content": "hi"}])

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_utils/test_llm_client.py -v`
Expected: FAIL — `AttributeError: <module 'evalforge.utils.llm_client'> does not have the attribute 'tracer'`

- [ ] **Step 3: Instrument `llm_client.py`**

In `evalforge/utils/llm_client.py`, replace lines 1-16 with:

```python
"""Model-agnostic LLM client using LiteLLM for judge evaluation and synthetic generation."""

import asyncio
from typing import Any

import litellm
import structlog
from litellm import acompletion, completion_cost
from opentelemetry import trace

from evalforge.config import get_settings

logger = structlog.get_logger(__name__)
tracer = trace.get_tracer(__name__)

# Suppress noisy LiteLLM logs in standard runs
litellm.suppress_debug_info = True
```

Replace the body of `complete` (originally lines 49-99, from `selected_model = model or self.default_model` through the final `raise RuntimeError(...)`) with:

```python
        selected_model = model or self.default_model
        attempt = 0
        last_err: Exception | None = None

        with tracer.start_as_current_span(
            "evalforge.llm.complete",
            attributes={
                "gen_ai.system": "litellm",
                "gen_ai.request.model": selected_model,
            },
        ) as span:
            while attempt < max_retries:
                try:
                    params: dict[str, Any] = {
                        "model": selected_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        **kwargs,
                    }
                    if response_format:
                        params["response_format"] = response_format

                    response = await acompletion(**params)

                    content = response.choices[0].message.content or ""
                    try:
                        cost = completion_cost(completion_response=response)
                    except Exception:
                        cost = 0.0

                    usage = getattr(response, "usage", None)
                    total_tokens = usage.total_tokens if usage else 0

                    span.set_attribute(
                        "gen_ai.response.model", getattr(response, "model", selected_model)
                    )
                    if usage:
                        span.set_attribute("gen_ai.usage.input_tokens", usage.prompt_tokens)
                        span.set_attribute("gen_ai.usage.output_tokens", usage.completion_tokens)
                    span.set_attribute("evalforge.cost_usd", float(cost or 0.0))

                    return content, float(cost or 0.0), total_tokens

                except Exception as exc:
                    last_err = exc
                    attempt += 1
                    wait_time = 2**attempt
                    logger.warning(
                        "LLM completion attempt failed",
                        model=selected_model,
                        attempt=attempt,
                        error=str(exc),
                        retry_in=wait_time,
                    )
                    if attempt < max_retries:
                        await asyncio.sleep(wait_time)

            if last_err is not None:
                span.record_exception(last_err)
            logger.error(
                "LLM completion exhausted all retries",
                model=selected_model,
                error=str(last_err),
            )
            raise RuntimeError(
                f"Failed LLM completion after {max_retries} attempts: {last_err}"
            ) from last_err
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_utils/test_llm_client.py -v`
Expected: PASS

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add evalforge/utils/llm_client.py tests/unit/test_utils/
git commit -m "feat(observability): add GenAI span attributes to LiteLLMClient"
```

---

### Task 9: Wire the Celery worker process — `celery_app.py`

**Files:**
- Modify: `evalforge/tasks/celery_app.py`
- Test: `tests/unit/test_tasks/__init__.py` (new, empty)
- Test: `tests/unit/test_tasks/test_celery_app.py` (new file)

**Interfaces:**
- Consumes: `evalforge.observability.logging.configure_structlog` (Task 5), `evalforge.observability.otel.configure_observability` (Task 4).

- [ ] **Step 1: Write the failing test**

Create `tests/unit/test_tasks/test_celery_app.py`:

```python
"""Tests for Celery worker observability init hook."""

from evalforge.tasks.celery_app import _init_worker_observability


def test_init_worker_observability_runs_without_error():
    _init_worker_observability()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/test_tasks/test_celery_app.py -v`
Expected: FAIL — `ImportError: cannot import name '_init_worker_observability'`

- [ ] **Step 3: Wire `celery_app.py`**

Replace the full contents of `evalforge/tasks/celery_app.py` with:

```python
"""Celery task configuration for EvalForge."""

import os

from celery import Celery
from celery.signals import worker_process_init
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

from evalforge.observability.logging import configure_structlog
from evalforge.observability.otel import configure_observability

REDIS_URL = os.getenv("EVALFORGE_REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "evalforge",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "evalforge.tasks.evaluation_tasks",
        "evalforge.tasks.experiment_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,
    worker_prefetch_multiplier=1,
    task_routes={
        "evalforge.tasks.evaluation_tasks.run_async_evaluation": {"queue": "evaluations"},
        "evalforge.tasks.evaluation_tasks.run_experiment_batch": {"queue": "experiments"},
    },
)


@worker_process_init.connect(weak=False)
def _init_worker_observability(**kwargs: object) -> None:
    """Configures OTel + structlog inside each forked Celery worker process."""
    configure_structlog()
    configure_observability()
    CeleryInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/test_tasks/test_celery_app.py -v`
Expected: PASS

- [ ] **Step 5: Run full unit suite + lint + mypy**

Run: `uv run pytest tests/unit -q && uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge`
Expected: all green

- [ ] **Step 6: Commit**

```bash
git add evalforge/tasks/celery_app.py tests/unit/test_tasks/
git commit -m "feat(observability): wire OTel + structlog into the Celery worker process"
```

---

### Task 10: `docker-compose.yaml` env passthrough + setup docs

**Files:**
- Modify: `docker-compose.yaml`
- Create: `docs/observability-setup.md`

**Interfaces:** none (docs + env wiring only, no code).

- [ ] **Step 1: Add env passthrough to `docker-compose.yaml`**

In `docker-compose.yaml`, under both the `api` service's `environment:` block and the `worker` service's `environment:` block, add these four lines (after the existing `EVALFORGE_REDIS_URL` line in each):

```yaml
      - EVALFORGE_GRAFANA_OTLP_ENDPOINT=${EVALFORGE_GRAFANA_OTLP_ENDPOINT:-}
      - EVALFORGE_GRAFANA_OTLP_INSTANCE_ID=${EVALFORGE_GRAFANA_OTLP_INSTANCE_ID:-}
      - EVALFORGE_GRAFANA_OTLP_API_KEY=${EVALFORGE_GRAFANA_OTLP_API_KEY:-}
      - LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY:-}
      - LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY:-}
```

- [ ] **Step 2: Write `docs/observability-setup.md`**

Create `docs/observability-setup.md`:

```markdown
# Observability Setup (Grafana Cloud + Langfuse, both free tier)

EvalForge exports OpenTelemetry traces, metrics, and logs to Grafana Cloud,
and LLM-generation spans (judge model calls, synthetic generation) to
Langfuse Cloud. Both are optional — with the env vars below unset, the app
runs normally and just skips exporting.

## 1. Grafana Cloud (free tier)

1. Sign up at https://grafana.com/auth/sign-up/create-user (free tier
   includes Tempo traces, Mimir metrics, and Loki logs).
2. In your Grafana Cloud stack, go to **Connections → Add new connection →
   OpenTelemetry (OTLP)**.
3. Copy the **OTLP endpoint URL** shown there — it looks like
   `https://otlp-gateway-prod-xx-xxxx.grafana.net/otlp`. This is your
   `EVALFORGE_GRAFANA_OTLP_ENDPOINT` (no trailing `/v1/traces` etc. — the
   app appends the per-signal path itself).
4. On the same page, copy the **Instance ID** (a numeric stack ID) — this is
   `EVALFORGE_GRAFANA_OTLP_INSTANCE_ID`.
5. Generate an **API token** with at least `metrics:write`, `logs:write`,
   and `traces:write` scopes (**Administration → API Keys** or the
   generate-token button on the OTLP connection page) — this is
   `EVALFORGE_GRAFANA_OTLP_API_KEY`.

## 2. Langfuse Cloud (free tier)

1. Sign up at https://cloud.langfuse.com.
2. Create a new project.
3. Go to **Project Settings → API Keys** and create a new key pair.
4. Copy the **Public Key** into `LANGFUSE_PUBLIC_KEY` and the **Secret Key**
   into `LANGFUSE_SECRET_KEY`. Leave `LANGFUSE_HOST` as the default
   `https://cloud.langfuse.com` unless you're self-hosting.

## 3. Fill in `.env`

```bash
EVALFORGE_GRAFANA_OTLP_ENDPOINT=https://otlp-gateway-prod-xx-xxxx.grafana.net/otlp
EVALFORGE_GRAFANA_OTLP_INSTANCE_ID=123456
EVALFORGE_GRAFANA_OTLP_API_KEY=glc_your_token_here

LANGFUSE_PUBLIC_KEY=pk-lf-your-public-key
LANGFUSE_SECRET_KEY=sk-lf-your-secret-key
LANGFUSE_HOST=https://cloud.langfuse.com
```

## 4. Verify

1. Start the stack: `docker-compose up -d --build` (or
   `uv run uvicorn evalforge.main:app --reload` locally).
2. Send a request to `POST /api/v1/evaluate` with any metric.
3. **Grafana Cloud:** open your stack → **Explore** → select the Tempo
   data source → search by `service.name = evalforge`. You should see a
   trace with an `evalforge.metric.evaluate` span. Switch the data source
   to Loki and search `{service_name="evalforge"}` for the same request's
   logs (they'll share a `trace_id`). Switch to Mimir/Prometheus and query
   `evalforge_eval_requests_total` for the counter.
4. **Langfuse:** open your project's **Traces** tab — if the metric you
   ran included an LLM-judge call, you'll see an `evalforge.llm.complete`
   generation with the model, token usage, and cost. Metrics that don't
   call an LLM (e.g. `length_checker`) won't appear here — only Grafana
   receives those, by design.
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yaml docs/observability-setup.md
git commit -m "docs(observability): add Grafana Cloud + Langfuse setup guide"
```

---

### Task 11: Final full-suite validation

**Files:** none (verification only).

- [ ] **Step 1: Run the complete gate**

Run: `uv run ruff check --fix . && uv run ruff format . && uv run mypy evalforge && uv run pytest tests/unit -v`

Expected: ruff reports no remaining issues, mypy reports `Success: no issues found`, and pytest shows all unit tests passing (25 original + new tests from Tasks 1, 2, 3, 4, 5, 7, 8, 9).

- [ ] **Step 2: Run integration tests (requires no external services — they mock the DB session)**

Run: `uv run pytest tests/integration -v`

Expected: all pass (these were already passing before Task 6 and must remain so).

- [ ] **Step 3: Confirm the app still boots with zero observability credentials**

Run: `uv run python -c "from evalforge.main import app; print('app import OK, observability no-op as expected')"`

Expected: prints the success message, no exceptions, no network attempts (nothing in `.env` points at real Grafana/Langfuse credentials in this dev environment).

- [ ] **Step 4: If any step above fails, fix and re-run this task's steps before proceeding — do not commit a red gate.**

No commit for this task — it's a verification checkpoint. If all green, the branch is ready for the check-mistakes / PR workflow.
