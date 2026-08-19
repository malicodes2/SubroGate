import os
import pytest
from pydantic import ValidationError
from backend.config import SubroGateSettings, get_settings

def test_default_configuration_loading():
    settings = SubroGateSettings()
    assert settings.APP_NAME == "SubroGate"
    assert settings.SUBROGATE_PORT in [8000, 8080]
    assert settings.SUBROGATE_GEMINI_MODEL == "gemini-3.5-flash"
    assert settings.SUBROGATE_ENV in ["development", "test", "production"]

def test_environment_override_model(monkeypatch):
    monkeypatch.setenv("SUBROGATE_GEMINI_MODEL", "gemini-3.5-pro")
    settings = SubroGateSettings()
    assert settings.SUBROGATE_GEMINI_MODEL == "gemini-3.5-pro"

def test_invalid_port_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        SubroGateSettings(SUBROGATE_PORT=99999)
    assert "SUBROGATE_PORT" in str(exc_info.value)

def test_invalid_negative_port():
    with pytest.raises(ValidationError) as exc_info:
        SubroGateSettings(SUBROGATE_PORT=-5)
    assert "SUBROGATE_PORT" in str(exc_info.value)

def test_invalid_model_name_raises_error():
    with pytest.raises(ValidationError) as exc_info:
        SubroGateSettings(SUBROGATE_GEMINI_MODEL="unsupported-gpt-model")
    assert "SUBROGATE_GEMINI_MODEL" in str(exc_info.value)

def test_invalid_log_level():
    with pytest.raises(ValidationError) as exc_info:
        SubroGateSettings(SUBROGATE_LOG_LEVEL="INVALID_LEVEL")
    assert "SUBROGATE_LOG_LEVEL" in str(exc_info.value)
