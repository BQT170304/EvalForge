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
