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
