import json

from app.workflow import _metric_values


def test_metric_values_parse_phase_filtered_prometheus_response() -> None:
    evidence = [
        {
            "tool": "query_prometheus",
            "response": json.dumps(
                {
                    "data": [
                        {
                            "metric": {"__name__": "render_frames_failed"},
                            "value": [1, "0"],
                        }
                    ]
                }
            ),
        }
    ]
    assert _metric_values(evidence) == {"render_frames_failed": 0.0}
