# Test Report

Version: 0.1.4
Date: 2026-08-30
Score: 9/10
Critical issues: 0
Verdict: PASS

## Executed evidence

- Packaging: editable install completed with Python 3.12.10 and Google ADK 2.1.0.
- Lint: `ruff check .` returned `All checks passed!`.
- Tests: `pytest` returned `11 passed, 1 warning in 1.15s`.
- Compile: `python -m compileall -q app` passed.
- Shell: both deployment scripts passed `bash -n`.
- Runtime audit: all five Google ADK/Grafana MCP markers present; zero Grafana write tools exposed; `--disable-write` enabled.
- Secret scan: zero credential candidates.
- Container: image `renderops-director:0.1.4` built successfully.
- HTTP smoke: health reported version 0.1.4; investigation returned six evidence items and three recovery actions.
- Browser smoke: Playwright completed the form flow and rendered the expected incident result.
- Cloud Run smoke: public home, health, and investigation endpoints returned HTTP 200.

## Known boundary

The public Cloud Run revision is a clearly labelled deterministic demo. Live Grafana MCP is implemented and containerized, but remains intentionally disabled until a least-privilege Grafana service-account token is attached through Secret Manager.
