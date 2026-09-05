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
    return len(providers.logger_provider._multi_log_record_processor._log_record_processors)


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
