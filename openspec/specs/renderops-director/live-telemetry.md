# Live Telemetry Pattern

Version: 0.2.1

A reproducible hackathon demo can use synthetic domain data without faking the integration. Export a bounded incident through a real OTLP endpoint, store it in Grafana Cloud, read it back through official Grafana MCP tools, and let Gemini correlate only evidence returned by those tools. Label the telemetry synthetic while keeping ingestion, storage, queries, model reasoning, and response delivery live.

Keep OTLP writer and Grafana reader credentials separate. The writer receives only metrics/logs/traces write scopes; the MCP service account remains Viewer and the MCP process starts with `--disable-write`.
