from typing import Any

from pydantic import BaseModel


class InvestigationResponse(BaseModel):
    status: str
    anomaly_date: str
    report: dict[str, Any]
    summary: dict[str, Any]
    evidence: list[dict[str, Any]]
    explanation: str


class HealthResponse(BaseModel):
    status: str
    service: str