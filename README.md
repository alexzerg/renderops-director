# RenderOps Director

RenderOps Director helps a render supervisor understand why a cinematic shot failed and recover only the affected frames.

**Live demo:** https://renderops-director-w6mw3t2ita-uc.a.run.app

**Hackathon:** [Agentic Cinema — Grafana track](https://agentic-cinema.devpost.com/)

![RenderOps Director](docs/production-live.png)

## The problem

A failed render is more than a red infrastructure alert. The supervisor needs to know which frames failed, what changed, whether the deadline is at risk, and whether a full rerender is really necessary.

The demo follows shot `SH-042`. A texture update pushes GPU memory to 96%, the final denoise pass starts failing, and 38 of 240 frames become unusable.

## Try the demo

1. Compare **Original plate** and **Failed render**.
2. Click **Investigate shot**.
3. Review the evidence from Prometheus, Loki, and Tempo.
4. Approve a five-frame canary.
5. Wait for Grafana to validate the new render.
6. Approve recovery of the 38 failed frames.
7. Watch the generated **Recovered shot**.

The recommended path costs `$35.90` instead of `$186.40` for a full rerender.

## What happens behind the button

The app sends render telemetry to Grafana Cloud through OpenTelemetry. A Gemini agent running on Google Cloud uses the official Grafana MCP server to query:

- Prometheus for frame failures, GPU pressure, queue delay, and cost;
- Loki for renderer and FFmpeg logs;
- Tempo for the failed denoise path and recovery traces.

The agent turns those signals into a recovery plan. Grafana is queried again after every approved step, so recovery does not unlock until the new telemetry passes its checks.

## Is the fix real?

The initial GPU out-of-memory incident is a controlled synthetic scenario. The approved work is real:

- FFmpeg runs inside Cloud Run;
- canary and recovery requests create new WebM files;
- the browser plays the file returned by the current request;
- exit code, duration, frame count, output size, logs, and traces are sent to Grafana;
- Grafana MCP reads that evidence back before the workflow continues.

No Grafana write tools are exposed. Expensive actions require human approval.

## Architecture

![Architecture](docs/architecture.png)

The editable diagram is available as [SVG](docs/architecture.svg). A more detailed evidence map is in [docs/grafana-evidence.md](docs/grafana-evidence.md).

## Run locally

Requirements: Python 3.11+, Docker, Google Cloud credentials, and optionally Grafana Cloud credentials for live mode.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
uvicorn app.main:app --reload
```

Open http://localhost:8000.

The default mode uses local demo data. Live settings are documented in [.env.example](.env.example). Tokens belong in environment variables or Google Secret Manager, never in the repository.

## Tests

```bash
python -m ruff check .
python -m pytest
python -m compileall app
docker build -t renderops-director:test .
```

## Submission files


- [Devpost copy](docs/devpost-submission.md)
- [Judge testing guide](docs/testing-guide.md)
- [Architecture](docs/architecture.png)

## Stack

Google ADK, Gemini on Vertex AI, Grafana Cloud, official `mcp-grafana`, Prometheus, Loki, Tempo, OpenTelemetry, Cloud Run, FastAPI, FFmpeg, and Playwright.

## License

MIT © 2026 Aleksei Chirkunov
