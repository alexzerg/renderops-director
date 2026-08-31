# Architecture

```mermaid
flowchart LR
  O[Render Supervisor] -->|Shot + deadline objective| UI[FastAPI Operator Console]
  UI --> S[Bounded OpenTelemetry scenario]
  S -->|OTLP metrics + logs + traces| GC[Grafana Cloud]
  UI --> R[Google ADK Runner]
  R --> G[Gemini on Vertex AI]
  G --> T{ADK McpToolset}
  T -->|Interactive dev: Streamable HTTP + OAuth| HC[Hosted Grafana Cloud MCP]
  T -->|Cloud Run: stdio + service token| OSS[Official mcp-grafana v1.3.0]
  HC --> GC
  OSS --> GC
  GC --> P[Prometheus metrics]
  GC --> L[Loki logs]
  GC --> TP[Tempo traces]
  GC --> A[Alerts + dashboards]
  G --> D[Structured evidence-backed recovery decision]
  D --> H[Human approval gate]
```

The live agent has a read-only MCP allowlist. It can investigate and prepare a recovery plan, but it cannot alter dashboards, incidents, alerts, infrastructure, or render workloads.
