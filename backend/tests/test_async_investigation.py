import time
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.main import app
from backend.models.case import CaseStatus
from backend.models.investigation import DisputeInvestigationRequest, CaseDisputeMetadata
from backend.services.async_investigation_worker import AsyncInvestigationWorker, AsyncJobStatus
from backend.services.telemetry_simulator import TelemetryEventSimulator
from backend.services.case_service import CaseService


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_async_state():
    """Resets worker and repository state before each test."""
    worker = AsyncInvestigationWorker()
    worker.clear_state()
    case_service = CaseService()
    case_service.repository.clear()
    yield
    worker.clear_state()
    case_service.repository.clear()


def test_normal_async_completion(client):
    """
    Submits an investigation asynchronously, immediately receives PROCESSING status,
    and verifies completion in Firestore.
    """
    sim_event = TelemetryEventSimulator.generate_shock_breach_event(container_id="MSKU9082345")
    request_data = {
        "case_metadata": {
            "shipment_id": "MSKU9082345",
            "shipper_name": "Pacific Pharma Global Inc.",
            "carrier_name": "Apex Drayage Logistics LLC",
            "declared_value_usd": 100000.0,
            "claimed_loss_usd": 75000.0
        },
        "telemetry_csv": sim_event.csv_payload
    }

    # 1. Submit Async
    response = client.post("/api/investigation/submit-async", json=request_data)
    assert response.status_code == 202
    data = response.json()
    assert "case_id" in data
    assert "job_id" in data
    assert data["status"] in ["PROCESSING", "COMPLETED"]
    assert data["is_duplicate"] is False

    case_id = data["case_id"]

    # 2. Wait / Poll for background worker completion (typically < 1000ms)
    completed = False
    for _ in range(30):
        time.sleep(0.1)
        case_res = client.get(f"/api/cases/{case_id}")
        assert case_res.status_code == 200
        case_data = case_res.json()
        if case_data["status"] == CaseStatus.ASSESSMENT_READY.value:
            completed = True
            break

    assert completed is True
    assert case_data["normalized_timeline"] is not None
    assert len(case_data["normalized_timeline"]) >= 1
    assert case_data["assessment"] is not None
    assert case_data["assessment"]["potentially_responsible_party"] is not None


def test_duplicate_event_deduplication(client):
    """
    Ensures submitting identical telemetry events returns the existing case without spawning duplicate pipelines.
    """
    sim_event = TelemetryEventSimulator.generate_temperature_excursion_event(
        container_id="MSKU9082345",
        event_id="EVT-DEDUP-001"
    )
    request_data = {
        "case_metadata": {
            "shipment_id": "MSKU9082345",
            "carrier_name": "Apex Drayage Logistics LLC"
        },
        "telemetry_csv": sim_event.csv_payload
    }

    # First submission
    res1 = client.post("/api/investigation/submit-async?event_id=EVT-DEDUP-001", json=request_data)
    assert res1.status_code == 202
    data1 = res1.json()
    assert data1["is_duplicate"] is False
    case_id1 = data1["case_id"]

    # Second submission with same event ID
    res2 = client.post("/api/investigation/submit-async?event_id=EVT-DEDUP-001", json=request_data)
    assert res2.status_code == 202
    data2 = res2.json()
    assert data2["is_duplicate"] is True
    assert data2["case_id"] == case_id1


def test_telemetry_simulator_endpoint(client):
    """
    Verifies that the /simulate-telemetry-event endpoint produces valid events and launches async processing.
    """
    # 1. Simulate Shock event
    res_shock = client.post("/api/investigation/simulate-telemetry-event?event_type=SHOCK&container_id=MSKU1234567")
    assert res_shock.status_code == 202
    shock_data = res_shock.json()
    assert shock_data["case_id"] is not None

    # 2. Simulate Temperature event
    res_temp = client.post("/api/investigation/simulate-telemetry-event?event_type=TEMPERATURE&container_id=MSKU7654321")
    assert res_temp.status_code == 202
    temp_data = res_temp.json()
    assert temp_data["case_id"] is not None

    # 3. Simulate Clean Heartbeat
    res_clean = client.post("/api/investigation/simulate-telemetry-event?event_type=CLEAN&container_id=MSKU5555555")
    assert res_clean.status_code == 202


def test_async_failure_handling(client):
    """
    Simulates a failure during pipeline execution and verifies the case transitions to FAILED status.
    """
    worker = AsyncInvestigationWorker()

    with patch.object(worker.investigation_service, "process_investigation", side_effect=RuntimeError("Simulated OCR Model Timeout")):
        request = DisputeInvestigationRequest(
            case_metadata=CaseDisputeMetadata(shipment_id="FAIL-SHIP-01"),
            telemetry_csv="timestamp,latitude,longitude,temp_c,shock_g\n2026-08-15 14:00:00,34.0,-118.0,-18.0,0.5\n"
        )
        case, job, is_dup = worker.submit_investigation_async(request, custom_case_id="CASE-FAIL-01")
        assert case.status == CaseStatus.PROCESSING

        # Wait for failure
        time.sleep(0.2)
        failed_case = worker.case_service.get_case("CASE-FAIL-01")
        assert failed_case is not None
        assert failed_case.status == CaseStatus.FAILED

        # Check job status
        job_status = worker.get_job(job.job_id)
        assert job_status.status == AsyncJobStatus.FAILED
        assert "Simulated OCR Model Timeout" in job_status.error_message


def test_retry_and_recovery(client):
    """
    Verifies that a failed case can be retried and recovered to ASSESSMENT_READY status.
    """
    worker = AsyncInvestigationWorker()

    # 1. Create a failed case
    request = DisputeInvestigationRequest(
        case_metadata=CaseDisputeMetadata(
            shipment_id="RECOVERY-SHIP-01",
            shipper_name="Pacific Pharma Inc.",
            carrier_name="Apex Drayage LLC"
        ),
        telemetry_csv="timestamp,latitude,longitude,temp_c,shock_g\n2026-08-15 14:00:00,34.0,-118.0,-18.0,0.5\n2026-08-15 17:15:00,35.0,-117.0,12.4,4.2\n"
    )

    with patch.object(worker.investigation_service, "process_investigation", side_effect=RuntimeError("Temporary Network Flake")):
        case, job, is_dup = worker.submit_investigation_async(request, custom_case_id="CASE-RETRY-01")
        time.sleep(0.2)
        failed_case = worker.case_service.get_case("CASE-RETRY-01")
        assert failed_case.status == CaseStatus.FAILED

    # 2. Trigger Retry via API endpoint
    retry_res = client.post("/api/cases/CASE-RETRY-01/retry", json={"actor": "RECOVERY_BOT"})
    assert retry_res.status_code == 200
    retried_case = retry_res.json()
    assert retried_case["status"] in [CaseStatus.PROCESSING.value, CaseStatus.ASSESSMENT_READY.value]

    # 3. Wait for background completion
    recovered = False
    for _ in range(30):
        time.sleep(0.1)
        res = client.get("/api/cases/CASE-RETRY-01")
        if res.json()["status"] == CaseStatus.ASSESSMENT_READY.value:
            recovered = True
            break

    assert recovered is True
    final_case = client.get("/api/cases/CASE-RETRY-01").json()
    assert final_case["status"] == CaseStatus.ASSESSMENT_READY.value
    assert final_case["normalized_timeline"] is not None
