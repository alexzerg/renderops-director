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
