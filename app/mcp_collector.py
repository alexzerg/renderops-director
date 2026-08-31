"""Bounded direct MCP evidence collection for agent-response recovery."""

import asyncio
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _text_content(result: Any) -> str:
    return " ".join(getattr(item, "text", "") for item in result.content)[:6000]


async def collect_grafana_evidence(shot_id: str) -> tuple[list[str], list[dict[str, str]]]:
    """Query the same official read-only MCP server with a bounded deterministic plan."""
    grafana_url = os.environ.get("GRAFANA_URL", "").strip()
    token = os.environ.get("GRAFANA_SERVICE_ACCOUNT_TOKEN", "").strip()
    if not grafana_url or not token:
        raise RuntimeError("Grafana MCP credentials are unavailable for fallback collection")

    child_env = dict(os.environ)
    child_env["GRAFANA_URL"] = grafana_url
    child_env["GRAFANA_SERVICE_ACCOUNT_TOKEN"] = token
    params = StdioServerParameters(
        command=os.environ.get("GRAFANA_MCP_BINARY", "/usr/local/bin/mcp-grafana"),
        args=["-t", "stdio", "--disable-write"],
        env=child_env,
    )
    prometheus_uid = os.environ.get("GRAFANA_PROMETHEUS_UID", "grafanacloud-prom")
    loki_uid = os.environ.get("GRAFANA_LOKI_UID", "grafanacloud-logs")
    tempo_uid = os.environ.get("GRAFANA_TEMPO_UID", "grafanacloud-traces")
    normalized = shot_id.strip().upper()
    metric_queries = (
        "render_frames_failed",
        "render_gpu_memory_usage_percent",
        "render_gpu_utilization_percent",
        "render_queue_delay_minutes",
        "render_full_rerender_cost_usd_ratio",
        "render_failed_frames_cost_usd_ratio",
        "render_canary_cost_usd_ratio",
    )
    calls = tuple(
        (
            "query_prometheus",
            {
                "datasourceUid": prometheus_uid,
                "expr": expression,
                "queryType": "instant",
                "endTime": "now",
            },
        )
        for expression in metric_queries
    ) + (
        (
            "query_loki_logs",
            {
                "datasourceUid": loki_uid,
                "logql": '{service_name="render-worker"} |= "CUDA out of memory"',
                "startRfc3339": "now-2h",
                "endRfc3339": "now",
                "limit": 20,
                "format": "compact",
            },
        ),
        (
            "tempo_traceql-search",
            {
                "datasourceUid": tempo_uid,
                "query": (
                    '{ resource.service.name = "render-worker" && '
                    f'span.shot.id = "{normalized}" }}'
                ),
            },
        ),
    )

    evidence: list[dict[str, str]] = []
    tools: list[str] = []
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=15)
            for tool, arguments in calls:
                tools.append(tool)
                try:
                    result = await asyncio.wait_for(
                        session.call_tool(tool, arguments),
                        timeout=20,
                    )
                    evidence.append(
                        {
                            "tool": tool,
                            "response": _text_content(result),
                        }
                    )
                except TimeoutError:
                    evidence.append({"tool": tool, "response": "MCP call timed out"})
    return tools, evidence
