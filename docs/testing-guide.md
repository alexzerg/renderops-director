# Judge Testing Guide

## Public verification — no credentials required

1. Open https://renderops-director-w6mw3t2ita-uc.a.run.app.
2. Switch between **Original plate**, **Failed render**, and **Canary fix** and verify that all three previews play.
3. Confirm that the frame timeline marks failed frames and explains why editorial review is blocked.
4. Keep the default shot `SH-042` and mission, then click **Investigate shot**.
5. Wait up to 90 seconds for the live Gemini and Grafana MCP workflow.
6. Verify that the result includes:
   - runtime `Gemini + MCP`;
   - at least three evidence items;
   - failed-frame, GPU-memory, log, or trace evidence;
   - recovery cost `$35.90`;
   - avoided cost `$150.50 · 81%`;
   - exactly three recovery actions;
   - a human approval requirement.
7. Click **Approve canary** and verify:
   - `5 / 5` frames;
   - GPU memory `96% → 72%`;
   - successful Prometheus, Loki, and Tempo checks;
   - a real FFmpeg check with exit code, duration, frames, and output bytes;
   - the 38-frame recovery becomes enabled.
8. Click **Approve 38 frames** and verify `38 / 38`, `EDITORIAL READY`, and the recovered video.
9. Open **Runtime evidence** and verify MCP tool names such as `query_prometheus`, `query_loki_logs`, and `tempo_traceql-search`.

The initial cinematic GPU failure is synthetic and reproducible. Approved canary and recovery actions run real FFmpeg processing; their output files and actual execution telemetry are then verified through Grafana Cloud and official MCP queries.

## Health endpoint

```bash
curl -fsS https://renderops-director-w6mw3t2ita-uc.a.run.app/api/health
```

Expected indicators:

```json
{
  "status": "ok",
  "version": "0.8.0",
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
