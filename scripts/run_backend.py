#!/usr/bin/env python3
"""
Start the SubroGate FastAPI Backend
"""
import sys
import os
import uvicorn
from backend.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    print(f"Starting SubroGate Backend on {settings.SUBROGATE_HOST}:{settings.SUBROGATE_PORT}")
    print(f"Configured Model: {settings.SUBROGATE_GEMINI_MODEL}")
    uvicorn.run(
        "backend.main:app",
        host=settings.SUBROGATE_HOST,
        port=settings.SUBROGATE_PORT,
        reload=(settings.SUBROGATE_ENV == "development")
    )
