import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.config import get_settings

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

def test_health_endpoint_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "SubroGate"
    assert "version" in data
    assert "timestamp" in data
    assert "model" in data
    assert data["model"]["configured_model"] == get_settings().SUBROGATE_GEMINI_MODEL
    assert data["model"]["adk_compatible"] is True

def test_cors_headers_present(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers

def test_agent_registry_endpoint(client):
    response = client.get("/agents")
    assert response.status_code == 200
    catalog = response.json()
    assert catalog["catalog_version"] == "2.0.0"
    assert catalog["total_agents"] >= 3
    agent_ids = [a["agent_id"] for a in catalog["agents"]]
    assert "investigator-agent" in agent_ids
    assert "settlement-agent" in agent_ids
    assert "document-intelligence-agent" in agent_ids
