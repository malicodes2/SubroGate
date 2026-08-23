import os
import json
import logging
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class SubroGateSettings(BaseSettings):
    """
    Centralized Configuration for SubroGate.
    All configuration is loaded via environment variables and strictly validated.
    """
    APP_NAME: str = "SubroGate"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Agentic Forensic Assessment System for Cargo Transit Disputes"
    
    # Environment & Server
    SUBROGATE_ENV: str = Field(default="production", description="Runtime environment (development, staging, production, test)")
    SUBROGATE_HOST: str = Field(default="0.0.0.0", description="Server bind host")
    SUBROGATE_PORT: int = Field(
        default_factory=lambda: int(os.getenv("PORT", os.getenv("SUBROGATE_PORT", "8080"))),
        description="Server port (supports dynamic Cloud Run PORT)"
    )
    SUBROGATE_LOG_LEVEL: str = Field(default="INFO", description="Log level (DEBUG, INFO, WARNING, ERROR)")
    
    # Centralized Model Strategy - Configurable via SUBROGATE_GEMINI_MODEL
    SUBROGATE_GEMINI_MODEL: str = Field(
        default_factory=lambda: os.getenv("SUBROGATE_GEMINI_MODEL", "gemini-3.5-flash"),
        description="Configured eligible Google Gemini model name (e.g. gemini-3.5-flash, gemini-3.5-pro)"
    )
    
    # Google GenAI / Vertex AI Credentials
    GEMINI_API_KEY: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", None),
        description="Google AI Studio API Key"
    )
    GOOGLE_CLOUD_PROJECT: Optional[str] = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_PROJECT", os.getenv("GCP_PROJECT", None)),
        description="GCP Project ID for Vertex AI / Firestore"
    )
    GOOGLE_CLOUD_LOCATION: str = Field(
        default_factory=lambda: os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
        description="GCP Region for Vertex AI"
    )
    SUBROGATE_USE_VERTEX: bool = Field(
        default_factory=lambda: os.getenv("SUBROGATE_USE_VERTEX", "true").lower() in ("true", "1", "yes"),
        description="Set True to route through Vertex AI rather than AI Studio"
    )
    
    # Security & CORS (Configurable for GitHub Pages & Custom Domains)
    SUBROGATE_CORS_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            origin.strip() for origin in os.getenv(
                "CORS_ORIGINS",
                os.getenv(
                    "SUBROGATE_CORS_ORIGINS",
                    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000,https://malicodes2.github.io,*"
                )
            ).split(",") if origin.strip()
        ],
        description="Allowed CORS origins"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("SUBROGATE_PORT")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if v < 1 or v > 65535:
            raise ValueError(f"SUBROGATE_PORT must be between 1 and 65535, received: {v}")
        return v

    @field_validator("SUBROGATE_GEMINI_MODEL")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("SUBROGATE_GEMINI_MODEL cannot be empty.")
        clean_v = v.strip()
        # Accept standard Gemini model IDs (e.g. gemini-3.0-flash, gemini-3.5-pro, models/gemini-3.5-flash)
        if not (clean_v.lower().startswith("gemini-") or clean_v.lower().startswith("models/gemini-")):
            raise ValueError(f"SUBROGATE_GEMINI_MODEL must specify an eligible Gemini model (e.g. gemini-3.0-flash, gemini-3.5-pro), received: '{v}'")
        return clean_v

    @field_validator("SUBROGATE_LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper_v = v.upper()
        if upper_v not in valid_levels:
            raise ValueError(f"SUBROGATE_LOG_LEVEL must be one of {valid_levels}, received: {v}")
        return upper_v


_settings_instance: Optional[SubroGateSettings] = None

def get_settings() -> SubroGateSettings:
    """Singleton getter for application settings."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = SubroGateSettings()
    return _settings_instance

def reload_settings() -> SubroGateSettings:
    """Forces reloading of settings from environment."""
    global _settings_instance
    _settings_instance = SubroGateSettings()
    return _settings_instance
