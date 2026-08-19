import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.observability.tracer import observability, trace_span, OperationalSpanEvent
from backend.services.document_service import DocumentIntelligenceService
from backend.services.telemetry_engine import DeterministicTelemetryEngine
from backend.services.timeline_engine import DeterministicTimelineFusionEngine
from backend.services.case_service import CaseService
from backend.services.security_service import SecurityScreeningService
from backend.services.settlement_service import SettlementService
from backend.models.documents import ExtractedEIRData, HandoverCondition, GateEventType
from backend.models.investigation import CaseDisputeMetadata
from backend.models.case import ShipmentInfo, SourceDocumentRef, TelemetryRef
from backend.models.settlement import InboundCarrierMessage, CarrierObjectionType


@pytest.fixture
def client():
    return TestClient(app)


def test_observability_singleton_and_status(client):
    """Verifies OpenTelemetry tracer provider is initialized and status endpoint responds."""
    assert observability is not None
    tracer = observability.get_tracer()
    assert tracer is not None

    response = client.get("/api/observability/status")
    assert response.status_code == 200
    data = response.json()
    assert "service_name" in data
    assert "gcp_trace_active" in data
    assert "total_spans_in_memory" in data


def test_http_trace_middleware_attaches_header(client):
    """Verifies HTTP requests generate OpenTelemetry trace IDs in response headers."""
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-SubroGate-Trace-ID" in response.headers
    trace_id = response.headers["X-SubroGate-Trace-ID"]
    assert len(trace_id) == 32  # 128-bit hex trace ID


def test_document_extraction_span_creation():
    """Verifies document intelligence processing records OpenTelemetry span."""
    observability.memory_buffer.clear()
    doc_service = DocumentIntelligenceService()

    fake_pdf = b"%PDF-1.4 Mock EIR receipt with clean handover remarks"
    res = doc_service.process_document(
        file_bytes=fake_pdf,
        filename="origin_gate.pdf",
        mime_type="application/pdf",
        expected_container_id="MSKU9082345"
    )

    assert res is not None
    spans = observability.get_spans()
    eir_spans = [s for s in spans if "EIR Document Extraction" in s.step_name]
    assert len(eir_spans) >= 1
    span = eir_spans[0]
    assert span.category == "DOC_INTELLIGENCE"
    assert span.status == "SUCCESS"
    assert span.duration_ms >= 0


def test_telemetry_normalization_span_creation():
    """Verifies telemetry processing records OpenTelemetry span."""
    observability.memory_buffer.clear()
    csv_text = "timestamp,latitude,longitude,temp_c,shock_g\n2026-08-15 14:00:00,34.0,-118.0,-18.0,0.5\n2026-08-15 17:15:00,35.0,-117.0,12.4,4.2\n"

    res = DeterministicTelemetryEngine.process_csv(csv_text=csv_text)
    assert res.has_breach is True

    spans = observability.get_spans()
    tel_spans = [s for s in spans if "Telemetry" in s.step_name]
    assert len(tel_spans) >= 1
    assert tel_spans[0].category == "TELEMETRY"
    assert tel_spans[0].status == "SUCCESS"


def test_firestore_crud_spans():
    """Verifies Firestore repository operations record database spans."""
    observability.memory_buffer.clear()
    case_service = CaseService()

    case = case_service.create_case(
        shipment_info=ShipmentInfo(container_id="MSKU9082345"),
        actor="TESTER",
        custom_case_id="CASE-OBS-01"
    )

    retrieved = case_service.get_case("CASE-OBS-01")
    assert retrieved is not None

    spans = observability.get_spans_for_case("CASE-OBS-01")
    db_spans = [s for s in spans if "Firestore Case Persistence" in s.step_name]
    assert len(db_spans) >= 1
    assert db_spans[0].category == "DATABASE"


def test_security_screening_span_and_zero_secret_leak():
    """Verifies Model Armor security screening records span without leaking raw secrets."""
    observability.memory_buffer.clear()
    sec_service = SecurityScreeningService()

    from backend.models.settlement import OutboundDraft, DraftApprovalStatus, CarrierObjectionType
    draft = OutboundDraft(
        draft_id="DRF-TEST-SEC",
        case_id="CASE-SEC-01",
        identified_carrier_objection=CarrierObjectionType.DAMAGE_BEFORE_PICKUP,
        relevant_evidence_citations=[],
        draft_subject="Rebuttal",
        draft_body_markdown="Our margin is 35% profit and API Key is AIzaSyD123456789012345678901234567890.",
        status=DraftApprovalStatus.DRAFT,
        security_check_passed=False,
        next_recommended_action="Review"
    )

    report = sec_service.screen_draft(draft, case_id="CASE-SEC-01")
    assert report.verdict.value == "BLOCK"

    spans = observability.get_spans_for_case("CASE-SEC-01")
    sec_spans = [s for s in spans if "Security Screening" in s.step_name]
    assert len(sec_spans) >= 1
    sec_span = sec_spans[0]
    assert sec_span.category == "MODEL_ARMOR"
    assert sec_span.attributes.get("security.verdict") == "BLOCK"

    # Zero secret leakage in span attributes
    for k, v in sec_span.attributes.items():
        assert "AIzaSyD123456789012345678901234567890" not in str(v)


def test_case_execution_trace_api_endpoint(client):
    """Verifies GET /api/observability/cases/{case_id}/trace returns ordered execution events."""
    # Demo clean case
    client.post("/api/cases/demo/load-clean")

    response = client.get("/api/observability/cases/CASE-2026-DEMO-MSKU/trace")
    assert response.status_code == 200
    data = response.json()
    assert data["case_id"] == "CASE-2026-DEMO-MSKU"
    assert data["total_steps_count"] >= 5

    step_names = [s["step_name"] for s in data["spans"]]
    assert "Upload received" in step_names
    assert "EIR extracted" in step_names
    assert "Breach identified" in step_names
    assert "Custody interval matched" in step_names
    assert "Assessment generated" in step_names
    assert "Security check passed" in step_names


def test_no_chain_of_thought_leakage_in_spans():
    """Explicitly audits span attributes to guarantee no internal reasoning prompts are exposed."""
    with trace_span(
        name="Investigator Reasoning Test",
        case_id="CASE-AUDIT-01",
        attributes={
            "container_id": "MSKU9082345",
            "prompt_hidden": "DO NOT LOG INTERNAL THOUGHT TRACE",
            "chain_of_thought": "Private internal token analysis",
            "safe_metric": 42
        }
    ):
        pass

    spans = observability.get_spans_for_case("CASE-AUDIT-01")
    span = next(s for s in spans if s.step_name == "Investigator Reasoning Test")
    
    assert "safe_metric" in span.attributes
    assert "container_id" in span.attributes
    assert "prompt_hidden" not in span.attributes
    assert "chain_of_thought" not in span.attributes
