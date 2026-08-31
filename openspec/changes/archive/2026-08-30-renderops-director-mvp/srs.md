# Software Requirements Specification

Version: 0.1.0

## Components
- FastAPI web service and static operator console.
- Google ADK `Agent` and `Runner` using Gemini.
- Grafana MCP toolset with remote or stdio transport.
- Deterministic simulation adapter for public demo continuity.
- Cloud Run container containing the official `mcp-grafana` binary.

## Security boundary
The agent can observe but cannot mutate Grafana. Tokens are provided only through environment variables or Secret Manager. The browser never receives cloud credentials.
