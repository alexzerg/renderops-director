from typing import Literal

from pydantic import BaseModel, Field


class InvestigationRequest(BaseModel):
    shot_id: str = Field(default="SH-042", min_length=2, max_length=64)
    objective: str = Field(
        default="Find the render failure, estimate delivery risk, and propose the safest recovery.",
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
    evidence: list[EvidenceItem]
    recovery_plan: list[RecoveryAction]
    agent_narrative: str
    tools_used: list[str]
    approval_required: bool
