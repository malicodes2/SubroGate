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
