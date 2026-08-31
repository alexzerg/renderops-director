import pytest

from app.telemetry import _otlp_config, telemetry_enabled


def test_telemetry_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDEROPS_SEED_TELEMETRY", raising=False)
    assert telemetry_enabled() is False


def test_telemetry_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RENDEROPS_SEED_TELEMETRY", "true")
    assert telemetry_enabled() is True


def test_otlp_config_requires_all_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GRAFANA_OTLP_ENDPOINT", raising=False)
    monkeypatch.delenv("GRAFANA_OTLP_INSTANCE_ID", raising=False)
    monkeypatch.delenv("GRAFANA_OTLP_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="required to seed telemetry"):
        _otlp_config()


def test_otlp_config_builds_basic_auth_without_exposing_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GRAFANA_OTLP_ENDPOINT", "https://otlp.example/otlp/")
    monkeypatch.setenv("GRAFANA_OTLP_INSTANCE_ID", "123")
    monkeypatch.setenv("GRAFANA_OTLP_TOKEN", "glc_example")
    endpoint, headers = _otlp_config()
    assert endpoint == "https://otlp.example/otlp"
    assert headers["Authorization"].startswith("Basic ")
    assert "glc_example" not in headers["Authorization"]
