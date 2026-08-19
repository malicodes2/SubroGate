import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.case import (
    CaseModel,
    CaseStatus,
    ShipmentInfo,
    SourceDocumentRef,
    TelemetryRef,
    HumanApprovalEvent,
    NegotiationMessage,
    AuditEvent
)
from backend.services.case_repository import FirestoreCaseRepository, ConcurrencyConflictError, CaseNotFoundError
from backend.services.case_service import CaseService


@pytest.fixture
def repo():
    r = FirestoreCaseRepository()
    r.clear()
    return r


@pytest.fixture
def service(repo):
    return CaseService(repository=repo)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ==============================================================================
# 1. CREATE CASE TESTS
# ==============================================================================

def test_create_case_initial_state(service):
    shipment = ShipmentInfo(
        container_id="MSKU9082345",
        commodity="Frozen Organic Strawberries",
        declared_value_usd=75000.0,
        shipper_name="Pacific Berry Farms",
        carrier_name="Apex Drayage LLC"
    )
    doc_ref = SourceDocumentRef(
        document_id="DOC-001",
        filename="apm_gate_receipt.pdf",
        mime_type="application/pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=10240
    )
    tel_ref = TelemetryRef(
        device_id="SENS-8891",
        total_readings_count=120,
        breaches_detected_count=1,
        has_temp_excursion=True
    )

    case = service.create_case(
        shipment_info=shipment,
        document_refs=[doc_ref],
        telemetry_ref=tel_ref,
        actor="TEST_USER"
    )

    assert case.case_id.startswith("CASE-")
    assert case.status == CaseStatus.INGESTED
    assert case.version == 1
    assert case.shipment_info.container_id == "MSKU9082345"
    assert len(case.source_document_refs) == 1
    assert case.telemetry_ref.has_temp_excursion is True
    assert len(case.audit_events) == 1
    assert case.audit_events[0].event_type == "CASE_CREATED"
    assert case.audit_events[0].actor == "TEST_USER"


# ==============================================================================
# 2. READ CASE TESTS
# ==============================================================================

def test_get_case_by_id(service):
    case = service.create_case(custom_case_id="CASE-2026-TEST01")
    retrieved = service.get_case("CASE-2026-TEST01")

    assert retrieved is not None
    assert retrieved.case_id == "CASE-2026-TEST01"
    assert retrieved.status == CaseStatus.INGESTED


def test_get_nonexistent_case_returns_none(service):
    retrieved = service.get_case("CASE-NONEXISTENT")
    assert retrieved is None


# ==============================================================================
# 3. UPDATE CASE & OPTIMISTIC CONCURRENCY TESTS
# ==============================================================================

def test_update_case_increments_version(service):
    case = service.create_case(custom_case_id="CASE-2026-CONCURRENCY")
    assert case.version == 1

    # Transition status with matching version
    updated = service.transition_status(
        case_id="CASE-2026-CONCURRENCY",
        new_status=CaseStatus.PROCESSING,
        expected_version=1
    )
    assert updated.status == CaseStatus.PROCESSING
    assert updated.version == 2

    # Next update with version 2
    updated2 = service.transition_status(
        case_id="CASE-2026-CONCURRENCY",
        new_status=CaseStatus.ASSESSMENT_READY,
        expected_version=2
    )
    assert updated2.status == CaseStatus.ASSESSMENT_READY
    assert updated2.version == 3


def test_optimistic_concurrency_conflict_rejected(service):
    case = service.create_case(custom_case_id="CASE-2026-CONFLICT")
    assert case.version == 1

    # Attempt update with stale version 99 -> raises ConcurrencyConflictError
    with pytest.raises(ConcurrencyConflictError) as exc_info:
        service.transition_status(
            case_id="CASE-2026-CONFLICT",
            new_status=CaseStatus.PROCESSING,
            expected_version=99
        )
    assert "Optimistic concurrency conflict" in str(exc_info.value)


# ==============================================================================
# 4. STATUS TRANSITION LIFECYCLE TESTS
# ==============================================================================

def test_complete_status_lifecycle(service):
    """
    INGESTED -> PROCESSING -> ASSESSMENT_READY -> HUMAN_REVIEW -> APPROVED -> NEGOTIATION -> RESOLVED
    """
    case = service.create_case(custom_case_id="CASE-2026-LIFECYCLE")

    # INGESTED -> PROCESSING
    case = service.transition_status(case.case_id, CaseStatus.PROCESSING, actor="INGEST_PIPELINE")
    assert case.status == CaseStatus.PROCESSING

    # PROCESSING -> ASSESSMENT_READY
    case = service.transition_status(case.case_id, CaseStatus.ASSESSMENT_READY, actor="INVESTIGATOR_AGENT")
    assert case.status == CaseStatus.ASSESSMENT_READY

    # ASSESSMENT_READY -> HUMAN_REVIEW
    case = service.transition_status(case.case_id, CaseStatus.HUMAN_REVIEW, actor="ADJUSTER_DOE")
    assert case.status == CaseStatus.HUMAN_REVIEW

    # HUMAN_REVIEW -> APPROVED
    approval = HumanApprovalEvent(
        approval_id="APP-001",
        adjuster_name="Senior Adjuster Sarah Doe",
        allocated_liability_pct=100.0,
        notes="Verified reefer failure occurred on carrier equipment.",
        audit_badge_token="BADGE-SIG-9842"
    )
    case = service.record_human_approval(case.case_id, approval, actor="ADJUSTER_DOE")
    assert case.status == CaseStatus.APPROVED
    assert len(case.human_approvals) == 1

    # APPROVED -> NEGOTIATION (via negotiation message)
    msg = NegotiationMessage(
        message_id="MSG-001",
        sender_party="SubroGate Claims",
        recipient_party="Apex Drayage Legal Claims",
        message_text="Formal Demand of Subrogation Claim: $75,000.00 USD.",
        proposed_amount_usd=75000.0
    )
    case = service.append_negotiation_message(case.case_id, msg, actor="ADJUSTER_DOE")
    assert case.status == CaseStatus.NEGOTIATION
    assert len(case.negotiation_history) == 1

    # NEGOTIATION -> RESOLVED
    case = service.transition_status(case.case_id, CaseStatus.RESOLVED, actor="ADJUSTER_DOE", reason="Carrier paid full demand amount $75,000.")
    assert case.status == CaseStatus.RESOLVED
    assert case.closed_at_utc is not None

    # Check total audit trail
    assert len(case.audit_events) >= 6


# ==============================================================================
# 5. FAILED PROCESSING TRANSITION TESTS
# ==============================================================================

def test_failed_processing_transition(service):
    case = service.create_case(custom_case_id="CASE-2026-FAILURE")
    case = service.transition_status(
        case.case_id,
        CaseStatus.FAILED,
        actor="PIPELINE",
        reason="Fatal unparseable document scan and corrupted CSV."
    )

    assert case.status == CaseStatus.FAILED
    assert case.closed_at_utc is not None
    last_audit = case.audit_events[-1]
    assert last_audit.event_type == "STATUS_CHANGED"
    assert "Fatal unparseable" in last_audit.description


# ==============================================================================
# 6. NEGOTIATION HISTORY AND AUDIT LOGS TESTS
# ==============================================================================

def test_negotiation_history_accumulation(service):
    case = service.create_case(custom_case_id="CASE-2026-NEGO")

    # Message 1: Demand Notice
    msg1 = NegotiationMessage(
        message_id="MSG-01",
        sender_party="Subrogation Adjuster",
        recipient_party="Carrier Claims",
        message_type="FORMAL_DEMAND",
        message_text="Notice of Subrogation Claim: $50,000.00 USD.",
        proposed_amount_usd=50000.0
    )
    case = service.append_negotiation_message(case.case_id, msg1)

    # Message 2: Carrier Counter Offer
    msg2 = NegotiationMessage(
        message_id="MSG-02",
        sender_party="Carrier Claims",
        recipient_party="Subrogation Adjuster",
        message_type="COUNTER_OFFER",
        message_text="Carrier offers settlement of $40,000.00 USD without admission of liability.",
        proposed_amount_usd=40000.0
    )
    case = service.append_negotiation_message(case.case_id, msg2)

    assert len(case.negotiation_history) == 2
    assert case.negotiation_history[0].proposed_amount_usd == 50000.0
    assert case.negotiation_history[1].proposed_amount_usd == 40000.0


def test_arbitrary_audit_event_append(service):
    case = service.create_case(custom_case_id="CASE-2026-AUDIT")
    case = service.append_audit_event(
        case_id=case.case_id,
        event_type="SURVEYOR_REPORT_ATTACHED",
        description="Independent Marine Surveyor Report attached: Cargo total loss confirmed.",
        actor="SURVEYOR_OFFICE",
        metadata={"surveyor": "Lloyds Agency", "survey_cost_usd": 1500.0}
    )

    assert len(case.audit_events) == 2
    assert case.audit_events[1].event_type == "SURVEYOR_REPORT_ATTACHED"
    assert case.audit_events[1].metadata["survey_cost_usd"] == 1500.0


# ==============================================================================
# 7. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_create_and_get_case(client):
    payload = {
        "shipment_info": {
            "container_id": "MSKU9082345",
            "commodity": "Pharmaceuticals",
            "declared_value_usd": 150000.0,
            "carrier_name": "Apex Drayage LLC"
        },
        "actor": "TEST_ADJUSTER"
    }

    # POST /api/cases
    create_res = client.post("/api/cases", json=payload)
    assert create_res.status_code == 201
    created_case = create_res.json()
    case_id = created_case["case_id"]
    assert created_case["status"] == "INGESTED"
    assert created_case["version"] == 1

    # GET /api/cases/{case_id}
    get_res = client.get(f"/api/cases/{case_id}")
    assert get_res.status_code == 200
    assert get_res.json()["case_id"] == case_id

    # PATCH /api/cases/{case_id}/status
    patch_res = client.patch(
        f"/api/cases/{case_id}/status",
        json={"new_status": "PROCESSING", "actor": "AUTO_PIPELINE", "expected_version": 1}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "PROCESSING"
    assert patch_res.json()["version"] == 2

    # Concurrency conflict test via API (passing stale expected_version=1)
    conflict_res = client.patch(
        f"/api/cases/{case_id}/status",
        json={"new_status": "ASSESSMENT_READY", "expected_version": 1}
    )
    assert conflict_res.status_code == 409

    # POST /api/cases/{case_id}/approve
    approve_res = client.post(
        f"/api/cases/{case_id}/approve",
        json={
            "approval": {
                "approval_id": "APP-99",
                "adjuster_name": "Claims Lead Mark",
                "allocated_liability_pct": 100.0,
                "audit_badge_token": "SIG-HASH-9988"
            },
            "expected_version": 2
        }
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"
    assert approve_res.json()["version"] == 3


def test_api_list_cases_with_status_filter(client):
    # Create cases with distinct statuses
    client.post("/api/cases", json={"shipment_info": {"container_id": "CTR-1"}, "initial_status": "INGESTED"})
    client.post("/api/cases", json={"shipment_info": {"container_id": "CTR-2"}, "initial_status": "APPROVED"})

    list_res = client.get("/api/cases?status=APPROVED")
    assert list_res.status_code == 200
    cases = list_res.json()
    assert all(c["status"] == "APPROVED" for c in cases)
