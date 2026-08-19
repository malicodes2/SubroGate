from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

class SystemStatus(BaseModel):
    operational: bool = True
    environment: str = "development"
    uptime_seconds: float = 0.0

class ModelConfigInfo(BaseModel):
    configured_model: str = Field(..., description="Active configured model name from SUBROGATE_GEMINI_MODEL")
    provider: str = Field(default="Google GenAI / Vertex AI", description="Model provider")
    auth_configured: bool = Field(default=False, description="True if API key or GCP credentials are provided")
    use_vertex: bool = Field(default=False, description="True if Vertex AI routing is enabled")
    adk_compatible: bool = Field(default=True, description="Google Agent Development Kit runtime compatibility")

class HealthResponse(BaseModel):
    status: str = Field(default="healthy", description="System health status")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Server timestamp (UTC)")
    model: ModelConfigInfo = Field(..., description="Model configuration metadata")
    environment: str = Field(..., description="Runtime environment")

class ErrorDetail(BaseModel):
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
