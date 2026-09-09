# Phase 3: Observability — Langfuse + OpenTelemetry + Grafana Cloud

**Branch:** `feature/observability` → PR into `develop`
**Status:** Approved for implementation

## Goal

Give EvalForge production-grade observability across all three pillars —
traces, metrics, logs — using OpenTelemetry as the single instrumentation
layer, fanned out to two backends:

- **Grafana Cloud** (free tier): all traces, metrics, and logs — general
  service health (API latency, Celery task duration, DB/Redis calls, eval
  throughput, cost).
- **Langfuse Cloud** (free tier): only the LLM-generation spans (judge model
  calls, synthetic generation), rendered with Langfuse's LLM-specific UI
  (prompts, completions, token usage, cost per generation).

No new tracing SDK is introduced. Both destinations are reached via
standard OTLP/HTTP export from one `TracerProvider`; Langfuse receives a
filtered subset of the same spans Grafana receives in full.

## Non-goals

- No local OTel Collector / Tempo / Loki / Prometheus containers — export
  directly from the app process to the two cloud OTLP endpoints. Nothing to
  self-host, nothing new in `docker-compose.yaml` beyond env passthrough.
- No `langfuse` Python SDK dependency — pure OTel GenAI semantic
  conventions instead, matching GEMINI.md's existing "OpenTelemetry GenAI
  standards... pluggable tracing" statement.
- No Prometheus pull endpoint (`/metrics`) — metrics are pushed via OTLP,
  so a scrape endpoint would be a redundant second pipeline.
- Not touching `langsmith_*` / `arize_*` settings — out of scope, left as
  unused placeholders exactly as they are today.
- Not adding a `/health/ready` dependency-check endpoint — out of scope for
  this phase.

## Architecture

```
API request / Celery task
  └─ OTel spans (FastAPI/SQLAlchemy/Redis/Celery auto-instrumentation
                 + manual spans in orchestrator.py / llm_client.py,
                 GenAI spans carry gen_ai.* attributes)
       ├─ BatchSpanProcessor → OTLP/HTTP → Grafana Cloud Tempo   [ALL spans]
       └─ GenAISpanFilterProcessor → OTLP/HTTP → Langfuse /api/public/otel
                                                   [only spans with gen_ai.system attr]

Metrics → PeriodicExportingMetricReader → OTLP/HTTP → Grafana Cloud Mimir
Logs: structlog → stdlib logging (JSON stdout, trace_id/span_id injected)
      → OTel LoggingHandler → OTLP/HTTP → Grafana Cloud Loki
```

Both cloud destinations are OTLP/HTTP with Basic-auth headers — same
exporter class, different endpoint + credentials. Everything is
feature-flagged off (no exporters registered, zero overhead) when the
relevant env vars are empty, so local dev and CI need no real credentials.

## Module layout: `evalforge/observability/`

- **`otel.py`** — `configure_observability()`. Builds `TracerProvider`,
  `MeterProvider`, `LoggerProvider` with a shared `Resource`
  (`service.name`, `service.version`, `deployment.environment`).
  Registers the Grafana OTLP exporters (traces/metrics/logs) if
  `grafana_otlp_endpoint` is set. Registers the Langfuse filtered trace
  exporter if `langfuse_public_key`/`langfuse_secret_key` are set. Idempotent
  (guards against double-init, needed because Celery forks workers).
- **`filtering_processor.py`** — `GenAISpanFilterProcessor(SpanProcessor)`:
  delegates to an inner `BatchSpanProcessor`, only forwarding spans whose
  attributes include `gen_ai.system`.
- **`metrics.py`** — module-level instruments: `eval_requests_total`
  (counter), `eval_latency_ms` (histogram), `eval_cost_usd_total` (counter),
  `metric_failures_total` (counter). Plain module-level singletons, no
  wrapper class.
- **`logging.py`** — `configure_structlog()`: JSON renderer, merges
  `contextvars`, injects `trace_id`/`span_id` from the active OTel span
  into every log record, routes through
  `structlog.stdlib.ProcessorFormatter` into stdlib `logging` so the OTel
  `LoggingHandler` (registered on the root logger) forwards the same
  records to Loki.

## Instrumentation points (edits to existing files)

- `main.py`: call `configure_observability()` + `configure_structlog()` in
  `lifespan` startup; `FastAPIInstrumentor.instrument_app(app)`.
- `orchestrator.py`: span per `metric.evaluate()` call and per
  `evaluate_batch()`; increments `eval_requests_total` /
  `eval_latency_ms` / `metric_failures_total`.
- `llm_client.py`: span around `complete()` carrying `gen_ai.system`,
  `gen_ai.request.model`, `gen_ai.response.model`,
  `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, plus a custom
  `evalforge.cost_usd` attribute (cost isn't part of the official GenAI
  semconv). This is the attribute the Langfuse filter keys on.
- `celery_app.py`: `CeleryInstrumentor().instrument()` +
  `worker_process_init` signal calling `configure_observability()` /
  `configure_structlog()` (separate process from the API).
- One-line `SQLAlchemyInstrumentor().instrument(engine=...)` and
  `RedisInstrumentor().instrument()` calls where those clients are built.

## New dependencies (`pyproject.toml`)

```
opentelemetry-exporter-otlp-proto-http
opentelemetry-instrumentation-fastapi
opentelemetry-instrumentation-sqlalchemy
opentelemetry-instrumentation-celery
opentelemetry-instrumentation-redis
opentelemetry-sdk (already present, may need version bump for logs API)
```

## Config additions (`config.py` + `.env.example`)

Reuses existing `langfuse_public_key` / `langfuse_secret_key` /
`langfuse_host` fields (already present, currently unused). Adds:

```python
grafana_otlp_endpoint: str = ""       # e.g. https://otlp-gateway-prod-xx.grafana.net/otlp
grafana_otlp_instance_id: str = ""
grafana_otlp_api_key: str = ""
```

All default to `""` → observability fully opt-in; `configure_observability()`
checks each destination's settings independently before registering its
exporters.

## Resilience

`BatchSpanProcessor`/`PeriodicExportingMetricReader` export on background
threads; OTLP export failures are swallowed by the SDK's own retry/drop
logic and never raise into request handling — consistent with the
existing "metric failures must not kill a batch" principle.

## Testing

Unit tests (`tests/unit/test_observability/`), all using
`opentelemetry.sdk.trace.export.InMemorySpanExporter` — no real network
calls to Grafana/Langfuse:

- `GenAISpanFilterProcessor` forwards spans with `gen_ai.system` set, drops
  spans without it.
- `configure_observability()` registers zero exporters when all relevant
  settings are empty (no-op path), and the right exporter(s) when
  populated.
- structlog processor injects `trace_id`/`span_id` matching the current
  span context.
- `metrics.py` instruments record expected values (counter increments,
  histogram observations).

Existing test suite (`tests/unit`, `tests/integration`) must stay green;
`mypy --strict` and `ruff` must stay clean.

## Docs

New `docs/observability-setup.md`:
1. Creating a Grafana Cloud free-tier stack and locating the OTLP
   gateway endpoint / instance ID / API token.
2. Creating a Langfuse Cloud project and its public/secret keys.
3. Filling in the new `.env` vars.
4. How to confirm traces/metrics/logs are arriving in both UIs.

## Delivery

Single PR from `feature/observability` → `develop`, covering all three
pillars plus docs (per user decision — pillars are independent but the
overhead of 3 separate review/PR cycles isn't worth it here).
