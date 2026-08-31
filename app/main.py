from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import __version__
from app.models import InvestigationRequest, InvestigationResponse
from app.service import investigate, runtime_mode

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="RenderOps Director",
    version=__version__,
    description="Gemini + Grafana MCP incident director for cinematic rendering pipelines.",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    import os

    return {
        "status": "ok",
        "service": "renderops-director",
        "version": __version__,
        "agent_runtime": runtime_mode(),
        "grafana_transport": os.environ.get("GRAFANA_MCP_TRANSPORT", "demo"),
    }


@app.post("/api/investigate", response_model=InvestigationResponse)
async def run_investigation(request: InvestigationRequest) -> InvestigationResponse:
    try:
        return await investigate(request.shot_id, request.objective)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
