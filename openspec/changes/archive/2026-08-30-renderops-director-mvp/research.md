# Research

Version: 0.1.0

- Agentic Cinema requires Gemini and Google Cloud Agent Builder/ADK plus active partner runtime integration.
- Grafana track checks an actual official Grafana MCP connection; AI Observability alone is insufficient.
- Hosted Grafana Cloud MCP uses Streamable HTTP and OAuth 2.1 at `https://mcp.grafana.com/mcp`.
- Unattended Cloud Run should use the official OSS `mcp-grafana` process with a Grafana service-account token.
- ADK Python exposes remote and stdio MCP servers through `McpToolset`.
- Cloud Run is the target because it is Google-managed and can scale to zero.

Sources are linked in README.
