from app.service import _structured_response


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
