import os
import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from app.agent import root_agent
from app.demo import build_demo_brief
from app.models import InvestigationResponse

APP_NAME = "renderops_director"
USER_ID = "web_operator"
_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)


def runtime_mode() -> str:
    return os.environ.get("RENDEROPS_MODE", "demo").strip().lower()


async def investigate(shot_id: str, objective: str) -> InvestigationResponse:
    if runtime_mode() != "live":
        return build_demo_brief(shot_id)

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
    tools_used: list[str] = []

    async for event in _runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.function_call and part.function_call.name:
                    tools_used.append(part.function_call.name)
        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text or "" for part in event.content.parts).strip()

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
