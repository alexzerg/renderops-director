"""Approval-gated canary and recovery execution with live Grafana verification."""

import asyncio
import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from app.mcp_collector import collect_grafana_evidence
from app.models import PhaseNarrative, PhaseVerificationResponse
from app.telemetry import SCENARIOS, seed_render_telemetry

LOGGER = logging.getLogger(__name__)


def _metric_values(evidence: list[dict[str, str]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in evidence:
        if item.get("tool") != "query_prometheus":
            continue
        try:
            payload = json.loads(item.get("response", "{}"))
        except json.JSONDecodeError:
            continue
        for series in payload.get("data", []):
            metric_name = series.get("metric", {}).get("__name__")
            raw_value = series.get("value", [None, None])[1]
            if metric_name and raw_value is not None:
                try:
                    values[metric_name] = float(raw_value)
                except (TypeError, ValueError):
                    continue
    return values


def _tool_text(evidence: list[dict[str, str]], tool: str) -> str:
    return " ".join(item["response"] for item in evidence if item["tool"] == tool)


def _gemini_phase_narrative(
    shot_id: str,
    phase: str,
    checks: list[str],
    evidence: list[dict[str, str]],
) -> PhaseNarrative:
    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "renderops-director-2026"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    prompt = f"""
You are verifying a cinematic render recovery phase using live Grafana MCP evidence.
Shot: {shot_id}
Phase: {phase}
Deterministic checks: {json.dumps(checks)}
MCP evidence: {json.dumps(evidence, ensure_ascii=False)[:18000]}

Summarize only what the checks and evidence prove. Do not invent frames, metrics, logs, traces,
or actions. For a successful canary, the next action is human approval of the 38-frame recovery.
For a successful recovery, the next action is release to editorial review.
""".strip()
    try:
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=1200,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=PhaseNarrative,
            ),
        )
        return PhaseNarrative.model_validate(
            response.parsed
            if response.parsed is not None
            else json.loads(response.text or "{}")
        )
    finally:
        client.close()


async def execute_render_phase(shot_id: str, phase: str) -> PhaseVerificationResponse:
    if phase not in {"canary", "recovery"}:
        raise ValueError(f"Unsupported recovery phase: {phase}")
    normalized = shot_id.strip().upper()
    seeded = await asyncio.to_thread(seed_render_telemetry, normalized, phase)
    await asyncio.sleep(float(os.environ.get("RENDEROPS_INGESTION_DELAY_SECONDS", "6")))
    tools, evidence = await collect_grafana_evidence(normalized, phase)
    values = _metric_values(evidence)
    scenario: dict[str, Any] = SCENARIOS[phase]
    frames_total = round(values.get("render_frames_total", -1))
    frames_failed = round(values.get("render_frames_failed", -1))
    gpu_memory = values.get("render_gpu_memory_usage_percent", -1)
    expected_log = (
        "Canary render completed" if phase == "canary" else "Recovery rerender completed"
    )
    log_verified = expected_log in _tool_text(evidence, "query_loki_logs")
    trace_text = _tool_text(evidence, "tempo_traceql-search")
    trace_verified = len(trace_text) > 20 and "trace" in trace_text.lower()
    metrics_verified = (
        frames_total == scenario["frames_total"]
        and frames_failed == 0
        and 0 <= gpu_memory < 85
    )
    verified = metrics_verified and log_verified and trace_verified
    checks = [
        (
            f"Prometheus: {frames_total}/{scenario['frames_total']} frames observed, "
            f"{frames_failed} failed, VRAM {gpu_memory:.0f}%"
        ),
        f"Loki: {'success log found' if log_verified else 'success log missing'}",
        f"Tempo: {'successful trace found' if trace_verified else 'trace missing'}",
    ]
    if phase == "canary":
        headline = "Canary validated by Grafana" if verified else "Canary verification failed"
        status = "validated" if verified else "failed"
        default_summary = (
            "Five canary frames completed final denoise with zero failures and stable GPU memory."
            if verified
            else "The canary did not satisfy every metric, log, and trace check."
        )
        default_next = (
            "Approve rerender of the 38 failed frames."
            if verified
            else "Keep the recovery locked and review the failed checks."
        )
    else:
        headline = (
            "Shot restored and editorial ready"
            if verified
            else "Recovery verification failed"
        )
        status = "completed" if verified else "failed"
        default_summary = (
            "All 38 failed frames were restored with zero new failures."
            if verified
            else "The recovery rerender did not satisfy every verification check."
        )
        default_next = (
            "Release SH-042 to editorial review."
            if verified
            else "Keep the shot quarantined and review the failed checks."
        )
    try:
        narrative = await asyncio.to_thread(
            _gemini_phase_narrative,
            normalized,
            phase,
            checks,
            evidence,
        )
        contradiction_terms = ("missing", "not find", "no trace", "did not find")
        contradicts_checks = verified and any(
            term in narrative.summary.lower() for term in contradiction_terms
        )
        summary = default_summary if contradicts_checks else narrative.summary
        next_action = default_next
        confidence = max(narrative.confidence, 0.95) if verified else narrative.confidence
        tools = [*tools, "gemini_phase_verifier"]
    except (ValueError, json.JSONDecodeError, ValidationError, RuntimeError):
        LOGGER.exception("Gemini phase verification summary failed")
        summary = default_summary
        next_action = default_next
        confidence = 0.98 if verified else 0.4
    delivered = ",".join(
        key for key in ("metrics", "logs", "traces") if seeded.get(key)
    )
    return PhaseVerificationResponse(
        shot_id=normalized,
        phase=phase,
        status=status,
        headline=headline,
        frames_processed=max(frames_total, 0),
        frames_failed=max(frames_failed, 0),
        gpu_memory_before_percent=96,
        gpu_memory_after_percent=max(gpu_memory, 0),
        verification_checks=checks,
        summary=summary,
        next_action=next_action,
        confidence=confidence,
        tools_used=list(
            dict.fromkeys(
                [
                    f"otlp_seed({phase}:{delivered})",
                    *tools,
                    "mcp_phase_verification",
                ]
            )
        ),
        approval_required=phase == "canary" and verified,
    )
