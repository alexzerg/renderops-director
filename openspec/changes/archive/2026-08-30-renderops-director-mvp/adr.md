# ADR-001: ADK + dual Grafana MCP transports

Version: 0.1.0
Status: Accepted

## Decision
Use Google ADK for orchestration and expose official Grafana MCP tools through `McpToolset`. Support hosted Streamable HTTP for interactive development and the OSS stdio server for unattended Cloud Run. Keep a clearly labelled deterministic demo mode for credential-free evaluation.

## Consequences
The repository visibly and actually calls both required runtimes. Live deployment requires Grafana credentials, while demo deployment remains safe and reproducible. Write tools are excluded until an explicit human approval workflow is implemented.
