# Verification Plan

Version: 0.1.0

| Gate | Command | Pass condition |
| --- | --- | --- |
| Format/lint | `python -m ruff check .` | exit 0 and `All checks passed!` |
| Unit/integration | `python -m pytest` | exit 0 and zero failed |
| Compile | `python -m compileall app` | exit 0 |
| Dependency/runtime audit | static Python audit script | imports and MCP calls found, no write tools exposed |
| Container | `docker build -t renderops-director:test .` | exit 0 |
| HTTP smoke | run container and curl health/investigate | HTTP 200 and expected JSON keys |
| Browser | Playwright opens UI and runs demo | incident brief visible |
| Secret scan | tracked-file regex scan | zero candidate secrets |
