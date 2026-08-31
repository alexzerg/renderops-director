from typing import Literal

from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    shot_id: str = Field(default="SH-042", min_length=2, max_length=64)
    objective: str = Field(
        default="Find the failure, compare rerender costs, and propose the safest canary.",
        min_length=10,
        max_length=500,
    )


class EvidenceItem(BaseModel):
    source: Literal["alert", "metric", "log", "trace", "dashboard", "simulation"]
    title: str
    value: str
    signal: Literal["critical", "warning", "healthy", "context"]


class RecoveryAction(BaseModel):
    order: int
    action: str
    owner: str
    risk: Literal["low", "medium", "high"]
    requires_approval: bool


class IncidentPayload(BaseModel):
    status: Literal["critical", "degraded", "healthy"]
    headline: str
    diagnosis: str
    confidence: float = Field(ge=0, le=1)
    delivery_risk_minutes: int = Field(ge=0)
    recommended_cost_usd: float = Field(ge=0)
    avoided_cost_usd: float = Field(ge=0)
    avoided_cost_percent: float = Field(ge=0, le=100)
    evidence: list[EvidenceItem]
    recovery_plan: list[RecoveryAction]
    approval_required: bool


class InvestigationResponse(BaseModel):
    shot_id: str
    status: Literal["critical", "degraded", "healthy"]
    runtime: Literal["demo", "gemini-grafana-mcp"]
    headline: str
    diagnosis: str
    confidence: float = Field(ge=0, le=1)
    delivery_risk_minutes: int = Field(ge=0)
    recommended_cost_usd: float = Field(ge=0)
    avoided_cost_usd: float = Field(ge=0)
    avoided_cost_percent: float = Field(ge=0, le=100)
    evidence: list[EvidenceItem]
    recovery_plan: list[RecoveryAction]
    agent_narrative: str
    tools_used: list[str]
    approval_required: bool


class RecoveryRequest(BaseModel):
    shot_id: str = Field(default="SH-042", min_length=2, max_length=64)


class PhaseNarrative(BaseModel):
    summary: str
    next_action: str
    confidence: float = Field(ge=0, le=1)


class RenderExecutionResult(BaseModel):
    executor: Literal["ffmpeg"]
    exit_code: int
    duration_ms: int = Field(ge=0)
    frames_processed: int = Field(ge=0)
    output_bytes: int = Field(ge=0)
    sha256: str
    media_mime: Literal["video/webm"]
    media_base64: str


class PhaseVerificationResponse(BaseModel):
    shot_id: str
    phase: Literal["canary", "recovery"]
    status: Literal["validated", "completed", "failed"]
    headline: str
    frames_processed: int = Field(ge=0)
    frames_failed: int = Field(ge=0)
    gpu_memory_before_percent: float = Field(ge=0, le=100)
    gpu_memory_after_percent: float = Field(ge=0, le=100)
    verification_checks: list[str]
    summary: str
    next_action: str
    confidence: float = Field(ge=0, le=1)
    tools_used: list[str]
    execution: RenderExecutionResult | None = None
    approval_required: bool
