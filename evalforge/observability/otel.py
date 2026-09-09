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
    # Exclude OTel's own internal loggers so the OTLP log exporter's failure
    # logs (e.g. during a Grafana outage) don't get re-ingested and re-exported,
    # which would otherwise create a self-feeding export loop.
    otel_handler.addFilter(lambda record: not record.name.startswith("opentelemetry"))
    root_logger = logging.getLogger()
    root_logger.handlers = [
        h for h in root_logger.handlers if getattr(h, "name", None) != "evalforge.otel"
    ]
    root_logger.addHandler(otel_handler)


_configured_providers: ObservabilityProviders | None = None


def configure_observability(settings: Settings | None = None) -> ObservabilityProviders:
    """Builds and installs OTel providers from settings.

    Idempotent — safe to call more than once per process (e.g. Celery's
    worker_process_init firing per fork). The first call builds and installs
    the providers; subsequent calls return that same instance without
    rebuilding or attempting to re-install (the OTel API refuses to override
    already-set global providers and only logs a warning, so a naive
    unconditional rebuild would silently return providers that were never
    actually installed).
    """
    global _configured_providers
    if _configured_providers is not None:
        return _configured_providers
    resolved = settings or get_settings()
    providers = build_providers(resolved)
    install(providers)
    _configured_providers = providers
    return providers
