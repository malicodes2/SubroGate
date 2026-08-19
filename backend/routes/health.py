from datetime import datetime, timezone
from fastapi import APIRouter
from ..config import get_settings
from ..models.schemas import HealthResponse, ModelConfigInfo

router = APIRouter(tags=["Health & System"])

@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """
    Health check endpoint.
    Returns system status, active environment, and centralized model configuration.
    """
    settings = get_settings()
    has_auth = bool(settings.GEMINI_API_KEY or (settings.GOOGLE_CLOUD_PROJECT and settings.SUBROGATE_USE_VERTEX))

    return HealthResponse(
        status="healthy",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        timestamp=datetime.now(timezone.utc),
        model=ModelConfigInfo(
            configured_model=settings.SUBROGATE_GEMINI_MODEL,
            provider="Google GenAI / Vertex AI",
            auth_configured=has_auth,
            use_vertex=settings.SUBROGATE_USE_VERTEX,
            adk_compatible=True
        ),
        environment=settings.SUBROGATE_ENV
    )
