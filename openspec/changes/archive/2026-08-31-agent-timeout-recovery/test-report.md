# Agent Timeout Recovery Test Report

Version: 0.3.1
Score: 10/10
Critical issues: 0
Verdict: PASS

- The failing production request was measured at 226 seconds with no final event.
- Primary ADK timeout was forced to one second.
- Recovery returned HTTP 200 in 18 seconds.
- Response contained four live evidence items and three recovery actions.
- `query_prometheus`, `query_loki_logs`, and `tempo_traceql-search` executed through official MCP.
- `mcp_direct_collector` and `gemini_structured_normalizer` were both reported.
- Ruff passed; 24 tests passed; Docker build passed.
