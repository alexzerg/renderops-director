# Judge Testing Guide

## Public verification — no credentials required

1. Open https://renderops-director-w6mw3t2ita-uc.a.run.app.
2. Keep the default shot `SH-042` and mission.
3. Click **Investigate shot**.
4. Wait up to 90 seconds for the live Gemini and Grafana MCP workflow.
5. Verify that the result includes:
   - runtime `Gemini + MCP`;
   - at least three evidence items;
   - failed-frame, GPU-memory, log, or trace evidence;
   - recovery cost `$35.90`;
   - avoided cost `$150.50 · 81%`;
   - exactly three recovery actions;
   - a human approval requirement.
6. Open **Runtime evidence** and verify MCP tool names such as:
   - `query_prometheus`;
   - `query_loki_logs`;
   - `tempo_traceql-search`.

The cinematic telemetry is synthetic and reproducible. The OTLP ingestion, Grafana Cloud storage, official MCP queries, Gemini reasoning, and HTTP response are live.

## Health endpoint

```bash
curl -fsS https://renderops-director-w6mw3t2ita-uc.a.run.app/api/health
```

Expected indicators:

```json
{
  "status": "ok",
  "version": "0.3.0",
  "agent_runtime": "live",
  "grafana_transport": "stdio"
}
```

## Local verification

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m ruff check .
python -m pytest
python -m compileall app
docker build -t renderops-director:test .
```

## Trust boundary

- No Grafana write tools are exposed.
- `mcp-grafana` runs with `--disable-write`.
- Tokens are injected through Google Secret Manager.
- Render mutations require human approval.
