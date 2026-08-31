# RenderOps Director MVP Requirements

Version: 0.1.0

## Goal
Build a new, public, production-shaped web agent for the Agentic Cinema Grafana track. Gemini must reason over render-pipeline evidence obtained through the official Grafana MCP runtime and return an actionable, human-approved recovery brief.

## Functional requirements
1. Accept a cinematic shot ID and an investigation objective.
2. In live mode, run a Google ADK agent backed by Gemini on Vertex AI.
3. Expose official Grafana MCP tools to the agent through ADK `McpToolset`.
4. Limit the initial agent to read-only metrics, logs, traces, alerts, dashboards and links.
5. Provide deterministic demo mode without claiming it is live Grafana data.
6. Show evidence, diagnosis, confidence, recommended actions and approval boundaries.
7. Run as a web application and deploy to Google Cloud Run.

## Non-functional requirements
- No non-Google AI models or agent frameworks.
- No secrets in source control.
- Scale to zero on Cloud Run.
- Public OSI-approved license and reproducible setup.
