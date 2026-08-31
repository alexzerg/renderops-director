# Live Grafana Telemetry Requirements

Version: 0.2.1

1. Send production-shaped render metrics, logs, and traces to Grafana Cloud through OTLP.
2. Retrieve the evidence through official read-only Grafana MCP tools.
3. Use Gemini on Vertex AI through Google ADK to correlate the evidence.
4. Return structured evidence, recovery options, delivery risk, and a human approval boundary.
5. Keep all credentials outside the public repository and supply them through Secret Manager.
