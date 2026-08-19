"""
SubroGate Route Handlers
"""
from .health import router as health_router
from .telemetry import router as telemetry_router
from .documents import router as documents_router
from .investigation import router as investigation_router
from .cases import router as cases_router
from .settlement import router as settlement_router

__all__ = ["health_router", "telemetry_router", "documents_router", "investigation_router", "cases_router", "settlement_router"]
