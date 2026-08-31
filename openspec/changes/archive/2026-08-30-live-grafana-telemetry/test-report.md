# Live Grafana Test Report

Version: 0.2.1
Score: 10/10
Critical issues: 0
Verdict: PASS

## Evidence

- OTLP export: metrics=True, logs=True, traces=True.
- Prometheus MCP: `render_frames_failed` returned value 38.
- Loki MCP: query returned `CUDA out of memory` evidence.
- Tempo MCP: TraceQL returned the failed denoiser trace.
- Google ADK live runner called Grafana MCP tools and returned HTTP 200.
- Structured response contained five evidence entries and three recovery actions.
- Human approval remained required.
- Ruff passed and pytest returned 17 passed.
- Token values were never added to repository files.
