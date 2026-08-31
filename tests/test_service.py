from unittest.mock import Mock, patch

from app.service import _bounded_tool_response, _normalize_from_evidence, _structured_response


def test_structured_response_parses_agent_json() -> None:
    final_text = """
    {
      "status": "critical",
      "headline": "Shot delivery is blocked",
      "diagnosis": "GPU memory saturation caused denoiser failures.",
      "confidence": 0.94,
      "delivery_risk_minutes": 42,
      "evidence": [
        {"source": "metric", "title": "Failed frames", "value": "38", "signal": "critical"}
      ],
      "recovery_plan": [
        {"order": 1, "action": "Run a five-frame canary", "owner": "Render supervisor",
         "risk": "low", "requires_approval": true}
      ],
      "approval_required": true
    }
    """
    response = _structured_response(final_text, "sh-042", ["query_prometheus"])
    assert response.shot_id == "SH-042"
    assert response.runtime == "gemini-grafana-mcp"
    assert response.confidence == 0.94
    assert len(response.evidence) == 1
    assert len(response.recovery_plan) == 1
    assert response.tools_used == ["query_prometheus"]


def test_structured_response_falls_back_for_non_json() -> None:
    response = _structured_response("plain investigation", "SH-042", ["query_loki_logs"])
    assert response.status == "degraded"
    assert response.evidence == []
    assert response.agent_narrative == "plain investigation"


def test_bounded_tool_response_limits_context() -> None:
    rendered = _bounded_tool_response({"value": "x" * 7000})
    assert len(rendered) == 6000


def test_normalizer_builds_structured_live_response() -> None:
    parsed = {
        "status": "critical",
        "headline": "Denoiser failure blocks delivery",
        "diagnosis": "MCP evidence shows GPU memory saturation.",
        "confidence": 0.95,
        "delivery_risk_minutes": 42,
        "evidence": [
            {
                "source": "metric",
                "title": "Failed frames",
                "value": "38",
                "signal": "critical",
            }
        ],
        "recovery_plan": [
            {
                "order": 1,
                "action": "Review the failed frame range",
                "owner": "Render operator",
                "risk": "low",
                "requires_approval": False,
            },
            {
                "order": 2,
                "action": "Run a five-frame canary",
                "owner": "Lighting TD",
                "risk": "medium",
                "requires_approval": True,
            },
            {
                "order": 3,
                "action": "Release the failed-frame rerender",
                "owner": "Render supervisor",
                "risk": "medium",
                "requires_approval": True,
            },
        ],
        "approval_required": True,
    }
    fake_client = Mock()
    fake_client.models.generate_content.return_value = Mock(parsed=parsed, text=None)
    with patch("app.service.genai.Client", return_value=fake_client):
        response = _normalize_from_evidence(
            "No final response received.",
            "SH-042",
            "Find the render failure.",
            ["query_prometheus"],
            [{"tool": "query_prometheus", "response": "38 failed frames"}],
        )
    assert response.runtime == "gemini-grafana-mcp"
    assert len(response.evidence) == 1
    assert len(response.recovery_plan) == 3
    assert response.tools_used == ["query_prometheus", "gemini_structured_normalizer"]
    fake_client.close.assert_called_once_with()
