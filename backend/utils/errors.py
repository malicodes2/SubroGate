import logging
from typing import Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("subrogate.errors")

class SubroGateException(Exception):
    """Base exception for SubroGate."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

class ConfigurationError(SubroGateException):
    """Raised when environment or model configuration is invalid."""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, details=details)

class ModelUnavailableError(SubroGateException):
    """Raised when the specified Gemini model or API is unreachable."""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=status.HTTP_503_SERVICE_UNAVAILABLE, details=details)

class ValidationException(SubroGateException):
    """Raised when input data validation fails."""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, details=details)

def register_exception_handlers(app: FastAPI) -> None:
    """Registers standard exception handlers on the FastAPI application."""
    
    @app.exception_handler(SubroGateException)
    async def subrogate_exception_handler(request: Request, exc: SubroGateException):
        logger.error(f"Application error on {request.method} {request.url.path}: {exc.message} (details: {exc.details})")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": exc.__class__.__name__,
                    "message": exc.message,
                    "details": exc.details
                }
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Request validation error on {request.method} {request.url.path}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid request parameters or payload",
                    "details": {"errors": exc.errors()}
                }
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "type": "HTTPException",
                    "message": exc.detail,
                    "details": {}
                }
            }
        )
