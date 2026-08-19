from typing import Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
from ..services.telemetry_engine import DeterministicTelemetryEngine
from ..models.telemetry import (
    IncidentTelemetry,
    TelemetryThresholdConfig,
    DataQualityReport
)
from ..services.telemetry_parser import TelemetryParser

router = APIRouter(prefix="/api/telemetry", tags=["Deterministic Telemetry Engine"])

class ProcessTelemetryRequest(BaseModel):
    csv_content: str
    thresholds: Optional[TelemetryThresholdConfig] = None
    default_timezone: Optional[str] = None

@router.post("/process-csv", response_model=IncidentTelemetry)
def process_telemetry_csv(payload: ProcessTelemetryRequest) -> IncidentTelemetry:
    """
    Deterministically processes raw CSV telemetry data.
    Validates CSV, normalizes timestamps to UTC, checks data quality,
    and detects threshold breaches without LLM invocation.
    """
    if not payload.csv_content or not payload.csv_content.strip():
        raise HTTPException(status_code=400, detail="CSV content cannot be empty.")

    incident = DeterministicTelemetryEngine.process_csv(
        csv_text=payload.csv_content,
        thresholds=payload.thresholds,
        default_timezone=payload.default_timezone
    )
    return incident

@router.post("/validate-quality", response_model=DataQualityReport)
def validate_telemetry_quality(payload: ProcessTelemetryRequest) -> DataQualityReport:
    """
    Audits raw CSV quality and returns detected integrity issues without running breach analysis.
    """
    _, report = TelemetryParser.parse_csv_content(
        csv_text=payload.csv_content,
        default_timezone=payload.default_timezone
    )
    return report
