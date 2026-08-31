from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "renderops-director"
    assert body["agent_runtime"] == "demo"


def test_home_page() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "RenderOps Director" in response.text
    assert "Investigate shot" in response.text
    assert "Original plate" in response.text
    assert "Failed render" in response.text
    assert "Canary fix" in response.text


def test_demo_investigation() -> None:
    response = client.post(
        "/api/investigate",
        json={
            "shot_id": "SH-042",
            "objective": "Diagnose the failed frames and propose the safest recovery.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["shot_id"] == "SH-042"
    assert body["runtime"] == "demo"
    assert body["approval_required"] is True
    assert body["delivery_risk_minutes"] > 0
    assert body["recommended_cost_usd"] == 35.9
    assert body["avoided_cost_usd"] == 150.5
    assert body["avoided_cost_percent"] == 80.7


def test_approval_gated_phase_endpoints() -> None:
    from unittest.mock import AsyncMock, patch

    base = {
        "shot_id": "SH-042",
        "headline": "Verified",
        "frames_failed": 0,
        "gpu_memory_before_percent": 96,
        "verification_checks": ["Prometheus", "Loki", "Tempo"],
        "summary": "Live Grafana verification passed.",
        "confidence": 0.98,
        "tools_used": ["query_prometheus", "query_loki_logs", "tempo_traceql-search"],
    }
    cases = [
        (
            "/api/canary",
            {
                **base,
                "phase": "canary",
                "status": "validated",
                "frames_processed": 5,
                "gpu_memory_after_percent": 72,
                "next_action": "Approve rerender of 38 failed frames.",
                "approval_required": True,
            },
        ),
        (
            "/api/recovery",
            {
                **base,
                "phase": "recovery",
                "status": "completed",
                "frames_processed": 38,
                "gpu_memory_after_percent": 74,
                "next_action": "Release to editorial review.",
                "approval_required": False,
            },
        ),
    ]
    for endpoint, result in cases:
        with patch("app.main.execute_render_phase", new=AsyncMock(return_value=result)):
            response = client.post(endpoint, json={"shot_id": "SH-042"})
        assert response.status_code == 200
        assert response.json()["status"] == result["status"]
