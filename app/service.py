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
from app.models import IncidentPayload, InvestigationResponse
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
step must be non-mutating analysis or quarantine guidance. Any canary or rerender requires human
approval. Use delivery risk from evidence when available; otherwise use 0.

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
                max_output_tokens=2200,
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
                            "response": _bounded_tool_response(part.function_response.response),
                        }
                    )
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text or "" for part in event.content.parts).strip()

    first_pass = _structured_response(final_text, shot_id, tools_used)
    if first_pass.evidence and first_pass.recovery_plan:
        return first_pass
    if not tool_evidence:
        return first_pass
    try:
        return await asyncio.to_thread(
            _normalize_from_evidence,
            final_text,
            shot_id,
            objective,
            tools_used,
            tool_evidence,
        )
    except (ValueError, json.JSONDecodeError, ValidationError):
        LOGGER.exception("Structured Gemini normalization failed")
        return first_pass
