import asyncio
import json
import logging
import os
import uuid
from typing import Any

from google import genai
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import ValidationError

from app.agent import root_agent
from app.demo import build_demo_brief
from app.mcp_collector import collect_grafana_evidence
from app.models import EvidenceItem, IncidentPayload, InvestigationResponse, RecoveryAction
from app.telemetry import seed_render_telemetry, telemetry_enabled

APP_NAME = "renderops_director"
USER_ID = "web_operator"
LOGGER = logging.getLogger(__name__)
_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)


def runtime_mode() -> str:
    return os.environ.get("RENDEROPS_MODE", "demo").strip().lower()


def _fallback_response(
    final_text: str,
    shot_id: str,
    tools_used: list[str],
) -> InvestigationResponse:
    return InvestigationResponse(
        shot_id=shot_id.strip().upper(),
        status="degraded",
        runtime="gemini-grafana-mcp",
        headline="Gemini completed a live Grafana MCP investigation",
        diagnosis=final_text,
        confidence=0.8,
        delivery_risk_minutes=0,
        recommended_cost_usd=0,
        avoided_cost_usd=0,
        avoided_cost_percent=0,
        evidence=[],
        recovery_plan=[],
        agent_narrative=final_text,
        tools_used=list(dict.fromkeys(tools_used)),
        approval_required=True,
    )


def _structured_response(
    final_text: str,
    shot_id: str,
    tools_used: list[str],
) -> InvestigationResponse:
    try:
        start = final_text.index("{")
        end = final_text.rindex("}") + 1
        payload = json.loads(final_text[start:end])
        payload.update(
            {
                "shot_id": shot_id.strip().upper(),
                "runtime": "gemini-grafana-mcp",
                "agent_narrative": payload.get("diagnosis", final_text),
                "tools_used": list(dict.fromkeys(tools_used)),
            }
        )
        return InvestigationResponse.model_validate(payload)
    except (ValueError, json.JSONDecodeError, ValidationError):
        return _fallback_response(final_text, shot_id, tools_used)


def _bounded_tool_response(value: Any) -> str:
    try:
        rendered = json.dumps(value, default=str, ensure_ascii=False)
    except TypeError:
        rendered = str(value)
    return rendered[:6000]


def _metric_values(tool_evidence: list[dict[str, str]]) -> dict[str, float]:
    values: dict[str, float] = {}
    for item in tool_evidence:
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


def _apply_economic_outcome(
    response: InvestigationResponse,
    tool_evidence: list[dict[str, str]],
) -> InvestigationResponse:
    values = _metric_values(tool_evidence)
    full = values.get("render_full_rerender_cost_usd_ratio")
    failed = values.get("render_failed_frames_cost_usd_ratio")
    canary = values.get("render_canary_cost_usd_ratio")
    if full is None or failed is None or canary is None or full <= 0:
        return response
    recommended = round(failed + canary, 2)
    avoided = round(full - recommended, 2)
    avoided_percent = round(avoided / full * 100, 1)
    failed_frames = round(values.get("render_frames_failed", 0))
    queue_delay = round(values.get("render_queue_delay_minutes", 0))
    economics = EvidenceItem(
        source="metric",
        title="Recovery economics",
        value=(
            f"Canary ${canary:.2f} + failed-frame rerender ${failed:.2f} = "
            f"${recommended:.2f}, versus ${full:.2f} full rerender."
        ),
        signal="healthy",
    )
    evidence = [item for item in response.evidence if item.title != economics.title]
    evidence = [*evidence[:4], economics]
    recovery_plan = [
        RecoveryAction(
            order=1,
            action=f"Isolate and review the {failed_frames} failed frames without rerendering.",
            owner="Render operator",
            risk="low",
            requires_approval=False,
        ),
        RecoveryAction(
            order=2,
            action=f"Run a five-frame canary for ${canary:.2f} using the safe asset configuration.",
            owner="Lighting TD",
            risk="medium",
            requires_approval=True,
        ),
        RecoveryAction(
            order=3,
            action=(
                f"If the canary passes, rerender only {failed_frames} failed frames "
                f"for ${failed:.2f}."
            ),
            owner="Render supervisor",
            risk="medium",
            requires_approval=True,
        ),
    ]
    return response.model_copy(
        update={
            "headline": (
                f"Avoid full rerender: recover {response.shot_id} for "
                f"${recommended:.2f} and save {avoided_percent:.0f}%"
            ),
            "delivery_risk_minutes": queue_delay or response.delivery_risk_minutes,
            "recommended_cost_usd": recommended,
            "avoided_cost_usd": avoided,
            "avoided_cost_percent": avoided_percent,
            "evidence": evidence,
            "recovery_plan": recovery_plan,
            "approval_required": True,
        }
    )


def _normalize_from_evidence(
    final_text: str,
    shot_id: str,
    objective: str,
    tools_used: list[str],
    tool_evidence: list[dict[str, str]],
) -> InvestigationResponse:
    client = genai.Client(
        vertexai=True,
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", "renderops-director-2026"),
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1"),
    )
    evidence_json = json.dumps(tool_evidence, ensure_ascii=False)[:30000]
    prompt = f"""
You are the structured-output stage for RenderOps Director.
Shot: {shot_id.strip().upper()}
Objective: {objective}

Use ONLY facts present in the MCP function responses below. Do not invent a dashboard, alert,
metric, log, trace, cost, duration, or cause. When signals conflict, lower confidence and say so.
Return 3-5 concise evidence items and exactly three ordered recovery actions. The first recovery
step must isolate or review the failed range without mutation. The second must be a five-frame
canary requiring approval. The third must rerender only failed frames after the canary passes and
requires approval. Use delivery risk from evidence when available; otherwise use 0. When full,
failed-frame-only, and canary cost metrics exist, calculate recommended cost as canary plus
failed-frame-only cost, avoided cost versus full rerender, and avoided percent. Make the headline
state the production decision and savings, not just the technical symptom.

Primary agent output, which may be incomplete:
{final_text[:6000]}

MCP function responses:
{evidence_json}
""".strip()
    try:
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=4096,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
                response_mime_type="application/json",
                response_schema=IncidentPayload,
            ),
        )
        payload = IncidentPayload.model_validate(
            response.parsed
            if response.parsed is not None
            else json.loads(response.text or "{}")
        )
        normalized_tools = list(dict.fromkeys([*tools_used, "gemini_structured_normalizer"]))
        return InvestigationResponse(
            shot_id=shot_id.strip().upper(),
            runtime="gemini-grafana-mcp",
            agent_narrative=payload.diagnosis,
            tools_used=normalized_tools,
            **payload.model_dump(),
        )
    finally:
        client.close()


def _collector_fallback_response(
    shot_id: str,
    tools_used: list[str],
    tool_evidence: list[dict[str, str]],
) -> InvestigationResponse:
    source_by_tool = {
        "query_prometheus": ("metric", "Prometheus render metrics", "critical"),
        "query_loki_logs": ("log", "Loki renderer logs", "critical"),
        "tempo_traceql-search": ("trace", "Tempo critical path", "warning"),
    }
    evidence: list[EvidenceItem] = []
    for item in tool_evidence:
        source, title, signal = source_by_tool.get(
            item["tool"],
            ("dashboard", item["tool"], "context"),
        )
        evidence.append(
            EvidenceItem(
                source=source,
                title=title,
                value=item["response"][:180] or "MCP returned an empty response",
                signal=signal,
            )
        )
    return InvestigationResponse(
        shot_id=shot_id.strip().upper(),
        status="degraded",
        runtime="gemini-grafana-mcp",
        headline="Live Grafana evidence collected; structured synthesis degraded",
        diagnosis=(
            "The bounded MCP collector completed, but Gemini structured synthesis was unavailable. "
            "Review the attached live metric, log, and trace evidence before approving recovery."
        ),
        confidence=0.55,
        delivery_risk_minutes=0,
        recommended_cost_usd=0,
        avoided_cost_usd=0,
        avoided_cost_percent=0,
        evidence=evidence[:3],
        recovery_plan=[
            RecoveryAction(
                order=1,
                action="Review the collected metric, log, and trace evidence.",
                owner="Render operator",
                risk="low",
                requires_approval=False,
            ),
            RecoveryAction(
                order=2,
                action="Prepare a five-frame canary for supervisor review.",
                owner="Lighting TD",
                risk="medium",
                requires_approval=True,
            ),
            RecoveryAction(
                order=3,
                action="Approve rerender only after the canary validates memory behavior.",
                owner="Render supervisor",
                risk="medium",
                requires_approval=True,
            ),
        ],
        agent_narrative="Live MCP evidence is available; automated synthesis degraded safely.",
        tools_used=list(dict.fromkeys([*tools_used, "mcp_direct_collector"])),
        approval_required=True,
    )


async def investigate(shot_id: str, objective: str) -> InvestigationResponse:
    if runtime_mode() != "live":
        return build_demo_brief(shot_id)

    tools_used: list[str] = []
    tool_evidence: list[dict[str, str]] = []
    if telemetry_enabled():
        seeded = await asyncio.to_thread(seed_render_telemetry, shot_id)
        delivered = [name for name in ("metrics", "logs", "traces") if seeded.get(name)]
        tools_used.append(f"otlp_seed({','.join(delivered)})")
        await asyncio.sleep(float(os.environ.get("RENDEROPS_INGESTION_DELAY_SECONDS", "6")))

    collector_task = asyncio.create_task(collect_grafana_evidence(shot_id))
    session_id = uuid.uuid4().hex
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )
    prompt = (
        f"Investigate cinematic render shot {shot_id}. Objective: {objective}. "
        "Use Grafana MCP evidence before reaching a conclusion."
    )
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    final_text = "No final response received."

    async def consume_primary_agent() -> None:
        nonlocal final_text
        async for event in _runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.function_call and part.function_call.name:
                        tools_used.append(part.function_call.name)
                    if part.function_response and part.function_response.name:
                        tool_evidence.append(
                            {
                                "tool": part.function_response.name,
                                "response": _bounded_tool_response(
                                    part.function_response.response
                                ),
                            }
                        )
            if event.is_final_response() and event.content and event.content.parts:
                final_text = "".join(part.text or "" for part in event.content.parts).strip()

    timeout_seconds = float(os.environ.get("RENDEROPS_AGENT_TIMEOUT_SECONDS", "45"))
    try:
        async with asyncio.timeout(timeout_seconds):
            await consume_primary_agent()
    except TimeoutError:
        final_text = f"Primary agent exceeded the {timeout_seconds:.0f}-second time limit."
        LOGGER.warning(final_text)
    except Exception:
        final_text = "Primary agent failed before producing a final response."
        LOGGER.exception(final_text)

    first_pass = _structured_response(final_text, shot_id, tools_used)
    try:
        collector_tools, collector_evidence = await asyncio.wait_for(
            collector_task,
            timeout=35,
        )
        tools_used.extend(collector_tools)
        tools_used.append("mcp_direct_collector")
        tool_evidence.extend(collector_evidence)
    except Exception:
        LOGGER.exception("Direct MCP evidence collector failed")

    if first_pass.evidence and first_pass.recovery_plan:
        first_pass = first_pass.model_copy(
            update={"tools_used": list(dict.fromkeys(tools_used))}
        )
        return _apply_economic_outcome(first_pass, tool_evidence)
    if not tool_evidence:
        return first_pass
    try:
        normalized = await asyncio.to_thread(
            _normalize_from_evidence,
            final_text,
            shot_id,
            objective,
            tools_used,
            tool_evidence,
        )
        return _apply_economic_outcome(normalized, tool_evidence)
    except Exception:
        LOGGER.exception("Structured Gemini normalization failed")
        fallback = _collector_fallback_response(shot_id, tools_used, tool_evidence)
        return _apply_economic_outcome(fallback, tool_evidence)
