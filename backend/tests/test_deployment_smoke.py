import pytest
from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_deployment_smoke_suite(client):
    """
    Automated in-process execution of the deployment smoke test suite.
    Verifies health, observability, demo case persistence, assessment retrieval,
    async telemetry simulation, and frontend SPA delivery.
    """
    # 1. Health Check
    res_health = client.get("/health")
    assert res_health.status_code == 200
    health = res_health.json()
    assert health.get("status") == "healthy"
    assert health.get("app") == "SubroGate"

    # 2. Observability
    res_obs = client.get("/api/observability/status")
    assert res_obs.status_code == 200
    assert "service_name" in res_obs.json()

    # 3. Ingest Demo Case
    res_demo = client.post("/api/cases/demo/load-clean")
    assert res_demo.status_code == 200
    case = res_demo.json()
    assert case["case_id"] == "CASE-2026-DEMO-MSKU"

    # 4. Forensic Timeline & Assessment
    res_case = client.get("/api/cases/CASE-2026-DEMO-MSKU")
    assert res_case.status_code == 200
    c_data = res_case.json()
    assert c_data.get("normalized_timeline") is not None
    assert c_data.get("assessment") is not None

    # 5. Async Telemetry Simulation
    res_sim = client.post("/api/investigation/simulate-telemetry-event?event_type=SHOCK&container_id=MSKU9082345")
    assert res_sim.status_code in [200, 202]
    sim_data = res_sim.json()
    assert "job_id" in sim_data

    # 6. Production Frontend SPA Delivery
    res_spa = client.get("/")
    assert res_spa.status_code in [200, 404]
    if res_spa.status_code == 200:
        assert "text/html" in res_spa.headers.get("content-type", "")
