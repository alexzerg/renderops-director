# RenderOps Director — Devpost Submission

## Tagline

**The production agent that gets the shot back before the deadline moves.**

## One-sentence description

RenderOps Director is a Gemini-powered production coordinator that uses the official Grafana MCP runtime to trace failed cinematic frames across metrics, logs, and traces, compare rerender options, and prepare a human-approved recovery decision.

## Inspiration

A render failure is not just an infrastructure incident. It can block editorial review, waste expensive GPU time, and force artists, pipeline engineers, and render supervisors to manually correlate multiple observability systems while a delivery deadline keeps moving.

Most monitoring products stop at a red dashboard. We wanted an agent that answers the production question: **Which frames should we rerender, why, how long will recovery take, and what is the safest option?**

## What it does

Before running the investigation, the operator can watch the original shot plate, the visibly damaged final-denoise render, and the recovered five-frame canary. A frame timeline identifies exactly where the shot becomes unusable.

An operator then enters a shot ID and production objective. RenderOps Director:

1. sends a bounded, clearly labelled cinematic incident through the real Grafana Cloud OTLP endpoint;
2. invokes Gemini through Google Agent Development Kit on Vertex AI;
3. lets the agent call official read-only Grafana MCP tools;
4. retrieves Prometheus metrics, Loki logs, Tempo traces, alerts, and dashboard context;
5. correlates failed frames, GPU pressure, renderer errors, asset versions, retries, queue delay, and rerender cost;
6. compares a full rerender, failed-frame-only rerender, and five-frame canary;
7. returns an evidence-backed recovery plan with confidence, owners, delivery risk, and explicit human approval gates;
8. executes an approved five-frame canary and emits a new canary telemetry phase;
9. verifies 5/5 frames, zero failures, stable VRAM, a Loki success event, and a Tempo trace before unlocking the 38-frame recovery;
10. verifies the final 38/38 rerender and marks the recovered shot editorial ready.

For the public SH-042 scenario, it recommends a $4.20 canary followed by a $31.70 failed-frame-only rerender: $35.90 instead of a $186.40 full rerender, avoiding $150.50 (about 81%).

The public scenario uses synthetic render telemetry so anyone can reproduce it. The ingestion, Grafana storage, MCP queries, Gemini reasoning, and Cloud Run response are all live.

## How we built it

The application is a Python FastAPI service deployed to Google Cloud Run. Google ADK provides the agent and runner, with Gemini 2.5 Flash served through Vertex AI. ADK's `McpToolset` connects to the official `mcp-grafana` server over stdio inside the same container.

Before an investigation, an OpenTelemetry component exports production-shaped metrics, structured renderer logs, and a failed denoiser trace to Grafana Cloud. The agent retrieves that evidence using read-only MCP tools for Prometheus, Loki, and Tempo.

Because tool-heavy model responses can occasionally be truncated, the service captures bounded MCP function responses. If the primary agent does not return valid structured JSON, a second schema-constrained Gemini pass formats those same tool results without inventing evidence.

Security and control boundaries include:

- Grafana MCP starts with `--disable-write`;
- only an explicit read-tool allowlist is exposed;
- OTLP writer and MCP reader credentials are separate Secret Manager values;
- render mutations always require human approval;
- Cloud Run scales to zero and has a maximum of two instances.

## Challenges we ran into

### Proving partner integration rather than simulating it

A local JSON fixture would not demonstrate Grafana MCP. We built a full round trip: OpenTelemetry to Grafana Cloud, then Prometheus/Loki/Tempo evidence back through official MCP calls before Gemini reaches a conclusion.

### Reliable structured output after multiple tool calls

The agent sometimes completed its tool calls without returning complete JSON. We separated investigation from formatting: actual MCP responses are retained and passed to a Gemini structured-output normalizer only when needed.

### Safe automation

Automatic rerendering looks impressive but is risky and expensive. The agent is intentionally read-only. It can calculate and recommend a canary, but the render supervisor owns every mutating action.

### Building a credible cinematic scenario

Generic CPU alerts would make this another SRE demo. We modelled shot and frame identifiers, render passes, GPU memory saturation, asset versions, denoiser retries, queue delay, and alternative rerender costs.

## Accomplishments that we're proud of

- Real Google ADK and Gemini runtime on Vertex AI.
- Real official Grafana MCP calls in the public application.
- Live Prometheus, Loki, and Tempo round trip.
- A decision-oriented outcome rather than a chatbot response.
- Repeatable public demo requiring no judge credentials.
- Read-only observability and explicit human approval boundaries.
- Automated tests, CI, container verification, and repeated browser stability checks.

## What we learned

Observability becomes far more valuable when telemetry is translated into a domain decision. Metrics alone say that GPU memory is high. Correlated render context says that only 38 frames failed after an asset change, a five-frame canary costs far less than a full rerender, and the safest recovery can still make the editorial deadline.

We also learned that agent reliability improves when tool orchestration and output formatting are separate concerns. Preserving tool evidence creates a trustworthy recovery path when the first model response is incomplete.

## What's next

- Connect a real render scheduler such as OpenCue through an approval-gated adapter.
- Add asset and shot metadata from a production tracking system.
- Learn recovery playbooks from accepted operator decisions.
- Compare current telemetry with previous successful renders of the same shot.
- Add approval-backed canary execution and automatic post-canary verification.
- Extend cost forecasting across GPU types, regions, and delivery scenarios.

## Built with

Google Cloud Run, Vertex AI, Gemini 2.5 Flash, Google Agent Development Kit, Google Gen AI SDK, Grafana Cloud, official Grafana MCP, Prometheus, Loki, Tempo, OpenTelemetry, FastAPI, Docker, GitHub Actions, Playwright, Python, and Secret Manager.

## Links

- Live application: https://renderops-director-w6mw3t2ita-uc.a.run.app
- Source code: https://github.com/alexzerg/renderops-director
