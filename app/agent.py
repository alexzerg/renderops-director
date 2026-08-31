import os
from collections.abc import Sequence

from google.adk.agents import Agent
from google.adk.tools import BaseTool, FunctionTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import (
    StdioConnectionParams,
    StreamableHTTPConnectionParams,
)
from google.genai import types
from mcp import StdioServerParameters

from app.demo import demo_telemetry

READ_ONLY_GRAFANA_TOOLS: tuple[str, ...] = (
    "alerting_manage_rules",
    "list_datasources",
    "list_prometheus_metric_names",
    "list_prometheus_label_names",
    "list_prometheus_label_values",
    "query_prometheus",
    "list_loki_label_names",
    "list_loki_label_values",
    "query_loki_logs",
    "query_loki_patterns",
    "tempo_traceql-search",
    "tempo_get-trace",
    "search_dashboards",
    "get_dashboard_summary",
    "generate_deeplink",
)

AGENT_INSTRUCTION = """
You are RenderOps Director, the incident commander for a cinematic rendering pipeline.

For every investigation:
1. Inspect active/firing alerts and identify the render service or shot.
2. Query Prometheus metrics matching the requested shot. Look for render_frames_failed,
   render_gpu_memory_usage_percent, render_gpu_utilization_percent,
   render_queue_delay_minutes, render_frame_duration_seconds,
   render_full_rerender_cost_usd, render_failed_frames_cost_usd, and
   render_canary_cost_usd.
3. Query Loki logs for the shot ID and the dominant renderer error pattern. Use the available
   Loki label discovery tools when needed; never guess a label name.
4. Query Tempo with TraceQL for spans whose shot.id attribute matches the shot ID.
5. Find a relevant dashboard and generate a human-review link when available.
6. Correlate the evidence before assigning a root cause. Clearly distinguish facts from inference.
7. Compare a full rerender, failed-frame-only rerender, and a five-frame canary. If all
   three cost metrics exist, calculate recommended_cost_usd as canary plus failed-frame-only cost,
   avoided_cost_usd versus a full rerender, and avoided_cost_percent.
8. The recovery plan must be: isolate the failed range; run a five-frame canary with approval;
   if it passes, rerender only failed frames with approval. Do not recommend a full rerender when
   the evidence supports the bounded path.

Your final response MUST be one compact JSON object with no Markdown fence or surrounding prose.
Use at most five evidence entries and exactly three recovery actions. Keep headline under 100
characters, diagnosis under 500 characters, and every title/value/action under 180 characters:
{
  "status": "critical|degraded|healthy",
  "headline": "short production outcome",
  "diagnosis": "evidence-backed root cause",
  "confidence": 0.0,
  "delivery_risk_minutes": 0,
  "recommended_cost_usd": 0.0,
  "avoided_cost_usd": 0.0,
  "avoided_cost_percent": 0.0,
  "evidence": [
    {"source": "alert|metric|log|trace|dashboard", "title": "...", "value": "...",
     "signal": "critical|warning|healthy|context"}
  ],
  "recovery_plan": [
    {"order": 1, "action": "...", "owner": "...", "risk": "low|medium|high",
     "requires_approval": true}
  ],
  "approval_required": true
}

Never claim a tool was used unless it was actually called. Never invoke write operations or make
changes to Grafana, alerts, incidents, dashboards, infrastructure, or render workloads. Recommend a
bounded canary before broad recovery. The human render supervisor owns every mutating action.
""".strip()


def _remote_toolset() -> McpToolset:
    grafana_url = os.environ.get("GRAFANA_URL", "").strip()
    if not grafana_url:
        raise RuntimeError("GRAFANA_URL is required for remote Grafana Cloud MCP")
    return McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=os.environ.get("GRAFANA_MCP_URL", "https://mcp.grafana.com/mcp"),
            headers={"X-Grafana-URL": grafana_url},
        ),
        tool_filter=list(READ_ONLY_GRAFANA_TOOLS),
    )


def _stdio_toolset() -> McpToolset:
    grafana_url = os.environ.get("GRAFANA_URL", "").strip()
    token = os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN", "").strip()
    if not grafana_url or not token:
        raise RuntimeError(
            "GRAFANA_URL and GRAFANA_SERVICE_ACCOUNT_TOKEN are required for stdio Grafana MCP"
        )
    child_env = dict(os.environ)
    child_env["GRAFANA_URL"] = grafana_url
    child_env["GRAFANA_SERVICE_ACCOUNT_TOKEN"] = token
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=os.environ.get("GRAFANA_MCP_BINARY", "/usr/local/bin/mcp-grafana"),
                args=["-t", "stdio", "--disable-write"],
                env=child_env,
            )
        ),
        tool_filter=list(READ_ONLY_GRAFANA_TOOLS),
    )


def build_tools(transport: str | None = None) -> Sequence[BaseTool | BaseToolset]:
    selected = (transport or os.environ.get("GRAFANA_MCP_TRANSPORT", "demo")).lower()
    if selected == "remote":
        return [_remote_toolset()]
    if selected == "stdio":
        return [_stdio_toolset()]
    if selected != "demo":
        raise ValueError(f"Unsupported GRAFANA_MCP_TRANSPORT: {selected}")
    return [FunctionTool(func=demo_telemetry)]


root_agent = Agent(
    model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    name="renderops_director",
    description="Diagnoses cinematic render-pipeline incidents using Gemini and Grafana MCP.",
    instruction=AGENT_INSTRUCTION,
    tools=list(build_tools()),
    generate_content_config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=3500),
)
