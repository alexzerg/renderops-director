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


def test_render_scenarios_have_expected_closed_loop_values() -> None:
    from app.telemetry import SCENARIOS

    assert SCENARIOS["failure"]["frames_failed"] == 38
    assert SCENARIOS["failure"]["gpu_memory"] == 96
    assert SCENARIOS["canary"]["frames_total"] == 5
    assert SCENARIOS["canary"]["frames_failed"] == 0
    assert SCENARIOS["canary"]["gpu_memory"] == 72
    assert SCENARIOS["recovery"]["frames_total"] == 38
    assert SCENARIOS["recovery"]["frames_failed"] == 0
