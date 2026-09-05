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
    monkeypatch.setenv(
        "EVALFORGE_GRAFANA_OTLP_ENDPOINT", "https://otlp-gateway-prod-xx.grafana.net/otlp"
    )
    monkeypatch.setenv("EVALFORGE_GRAFANA_OTLP_INSTANCE_ID", "123456")
    monkeypatch.setenv("EVALFORGE_GRAFANA_OTLP_API_KEY", "glc_fake_token")

    settings = Settings(_env_file=None)

    assert settings.grafana_otlp_endpoint == "https://otlp-gateway-prod-xx.grafana.net/otlp"
    assert settings.grafana_otlp_instance_id == "123456"
    assert settings.grafana_otlp_api_key == "glc_fake_token"


def test_langfuse_public_key_reads_from_unprefixed_env_var(monkeypatch):
    monkeypatch.delenv("EVALFORGE_LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-unprefixed")

    settings = Settings(_env_file=None)

    assert settings.langfuse_public_key == "pk-lf-unprefixed"


def test_langfuse_public_key_reads_from_prefixed_env_var(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.setenv("EVALFORGE_LANGFUSE_PUBLIC_KEY", "pk-lf-prefixed")

    settings = Settings(_env_file=None)

    assert settings.langfuse_public_key == "pk-lf-prefixed"
