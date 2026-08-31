from app.demo import build_demo_brief, demo_telemetry


def test_demo_telemetry_is_deterministic_and_normalized() -> None:
    first = demo_telemetry(" sh-042 ")
    second = demo_telemetry("SH-042")
    assert first == second
    assert first["shot_id"] == "SH-042"
    assert first["failed_frames"] < first["total_frames"]


def test_demo_brief_has_decision_and_human_gate() -> None:
    brief = build_demo_brief("SH-042")
    assert brief.status == "critical"
    assert brief.runtime == "demo"
    assert brief.confidence >= 0.9
    assert len(brief.evidence) >= 5
    assert len(brief.recovery_plan) == 3
    assert brief.approval_required is True
    assert any(action.requires_approval for action in brief.recovery_plan)
