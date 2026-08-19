import os
import time
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from .config import get_settings
from .services.logging import setup_structured_logging, get_logger
from .utils.errors import register_exception_handlers
from .routes.health import router as health_router
from .routes.telemetry import router as telemetry_router
from .routes.documents import router as documents_router
from .routes.investigation import router as investigation_router
from .routes.cases import router as cases_router
from .routes.settlement import router as settlement_router
from .routes.observability import router as observability_router
from .observability.tracer import trace_span

settings = get_settings()
setup_structured_logging(log_level=settings.SUBROGATE_LOG_LEVEL)
logger = get_logger("main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} ({settings.SUBROGATE_ENV})")
    logger.info(f"Active Gemini Model: {settings.SUBROGATE_GEMINI_MODEL}")
    yield
    logger.info(f"Gracefully shutting down {settings.APP_NAME}...")

def create_app() -> FastAPI:
    """Factory function for FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        lifespan=lifespan
    )

    # CORS Configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.SUBROGATE_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # OpenTelemetry HTTP Middleware
    @app.middleware("http")
    async def opentelemetry_trace_middleware(request, call_next):
        start_time = time.time()
        span_name = f"HTTP {request.method} {request.url.path}"
        with trace_span(
            name=span_name,
            category="HTTP",
            attributes={"http.method": request.method, "http.path": request.url.path}
        ) as span:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.duration_ms", duration_ms)
            
            trace_id = format(span.get_span_context().trace_id, "032x")
            response.headers["X-SubroGate-Trace-ID"] = trace_id
            return response

    # Global Exception Handlers
    register_exception_handlers(app)

    # Mount Route Handlers
    app.include_router(health_router)
    app.include_router(telemetry_router)
    app.include_router(documents_router)
    app.include_router(investigation_router)
    app.include_router(cases_router)
    app.include_router(settlement_router)
    app.include_router(observability_router)

    # Mount Production Frontend (React SPA) if built dist directory is present
    dist_paths = [
        Path(__file__).parent.parent / "frontend" / "dist",
        Path("/app/frontend/dist"),
        Path("frontend/dist")
    ]
    
    frontend_dist = next((p for p in dist_paths if p.exists() and (p / "index.html").exists()), None)
    if frontend_dist:
        logger.info(f"Mounting production frontend build from: {frontend_dist}")
        app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
        
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # If path matches a static file, return it, otherwise fallback to index.html for React SPA router
            target_file = frontend_dist / full_path
            if full_path and target_file.exists() and target_file.is_file():
                return FileResponse(target_file)
            return FileResponse(frontend_dist / "index.html")

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    # Support dynamic PORT environment variable (standard in Google Cloud Run)
    port = int(os.environ.get("PORT", settings.SUBROGATE_PORT))
    uvicorn.run(
        "backend.main:app",
        host=settings.SUBROGATE_HOST,
        port=port,
        reload=(settings.SUBROGATE_ENV == "development")
    )
