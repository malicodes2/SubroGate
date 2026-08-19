import pytest
from backend.config import get_settings
from backend.main import create_app
from backend.agents.base import BaseForensicAgent
from fastapi.testclient import TestClient

def test_foundation_architecture_integrity():
    """Verifies that all foundational components integrate cleanly."""
    settings = get_settings()
    assert settings.APP_NAME == "SubroGate"
    assert settings.SUBROGATE_GEMINI_MODEL.startswith("gemini-")

    # Agent foundation check
    agent = BaseForensicAgent(agent_name="IntegrityAgent")
    assert agent.model_name == settings.SUBROGATE_GEMINI_MODEL
    assert agent.agent_name == "IntegrityAgent"

    # App factory & client check
    app = create_app()
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
