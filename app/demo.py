from app.models import EvidenceItem, InvestigationResponse, RecoveryAction


def demo_telemetry(shot_id: str) -> dict:
    """Return deterministic fictional telemetry for credential-free demonstrations."""
    normalized = shot_id.strip().upper()
    return {
        "shot_id": normalized,
        "alert": "Render completion SLO breached for 11 minutes",
        "gpu_utilization": 17,
        "gpu_memory_percent": 96,
        "failed_frames": 38,
        "total_frames": 240,
        "log_pattern": "CUDA out of memory while allocating denoiser tile buffer",
        "trace_bottleneck": "denoise.final-pass (p99 92.4s, 8 retries)",
        "dashboard": "Render Farm / Sequence 12 / Night Exterior",
        "queue_delay_minutes": 23,
    }


def build_demo_brief(shot_id: str) -> InvestigationResponse:
    data = demo_telemetry(shot_id)
    evidence = [
        EvidenceItem(
            source="simulation",
            title="Demo boundary",
            value="Fictional but production-shaped Grafana telemetry; no live account queried.",
            signal="context",
        ),
        EvidenceItem(
            source="alert",
            title="Render completion SLO",
            value=data["alert"],
            signal="critical",
        ),
        EvidenceItem(
            source="metric",
            title="GPU pressure",
            value=(
                f"utilization {data['gpu_utilization']}% · memory {data['gpu_memory_percent']}% · "
                f"{data['failed_frames']}/{data['total_frames']} frames failed"
            ),
            signal="critical",
        ),
        EvidenceItem(
            source="log",
            title="Dominant Loki pattern",
            value=data["log_pattern"],
            signal="critical",
        ),
        EvidenceItem(
            source="trace",
            title="Tempo critical path",
            value=data["trace_bottleneck"],
            signal="warning",
        ),
        EvidenceItem(
            source="dashboard",
            title="Operator view",
            value=data["dashboard"],
            signal="context",
        ),
    ]
    recovery = [
        RecoveryAction(
            order=1,
            action="Quarantine the 38 failed frames so healthy workers stop retrying them.",
            owner="Render operator",
            risk="low",
            requires_approval=False,
        ),
        RecoveryAction(
            order=2,
            action="Requeue a five-frame canary with 25% smaller denoiser tiles.",
            owner="Lighting TD",
            risk="medium",
            requires_approval=True,
        ),
        RecoveryAction(
            order=3,
            action="If the canary stays below 85% GPU memory, release the remaining frames.",
            owner="Render supervisor",
            risk="medium",
            requires_approval=True,
        ),
    ]
    return InvestigationResponse(
        shot_id=data["shot_id"],
        status="critical",
        runtime="demo",
        headline="Denoiser memory saturation is stalling final-frame delivery",
        diagnosis=(
            "GPU compute is mostly idle while memory remains saturated. Loki and Tempo signals "
            "align on repeated final-pass denoiser allocation failures, making a tile-size "
            "regression the most likely root cause rather than capacity exhaustion."
        ),
        confidence=0.93,
        delivery_risk_minutes=data["queue_delay_minutes"] + 19,
        evidence=evidence,
        recovery_plan=recovery,
        agent_narrative=(
            "The safest path is a bounded canary, not a full rerun. The director has prepared the "
            "recovery sequence but will not execute workload changes without human approval."
        ),
        tools_used=[
            "demo_telemetry (simulates alerting_manage_rules)",
            "demo_telemetry (simulates query_prometheus)",
            "demo_telemetry (simulates query_loki_logs)",
            "demo_telemetry (simulates tempo_traceql-search)",
        ],
        approval_required=True,
    )
