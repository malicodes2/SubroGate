import io
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.investigation import (
    CustodyRole,
    CaseDisputeMetadata,
    DisputeInvestigationRequest,
    DisputeInvestigationResponse,
    EvidenceBackedAssessment
)
from backend.models.documents import (
    ExtractedEIRData,
    GateEventType,
    HandoverCondition,
    FieldEvidence
)
from backend.models.telemetry import (
    TelemetryThresholdConfig,
    IncidentTelemetry
)
from backend.services.timeline_engine import DeterministicTimelineFusionEngine
from backend.services.investigation_service import DisputeInvestigationService
from backend.services.telemetry_engine import DeterministicTelemetryEngine


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# Sample CSVs for Breach-Before and Breach-After Scenarios
CSV_TEMP_BREACH_BEFORE_HANDOVER = """timestamp,temperature_c,shock_g,latitude,longitude
2026-06-15T10:00:00Z,-18.5,0.2,34.0522,-118.2437
2026-06-15T11:30:00Z,12.5,0.4,34.0525,-118.2440
2026-06-15T12:30:00Z,14.8,0.3,34.0530,-118.2445
2026-06-15T13:30:00Z,11.2,0.2,34.0535,-118.2450
2026-06-15T14:30:00Z,-18.2,0.3,34.0540,-118.2460
2026-06-15T16:00:00Z,-19.0,0.2,34.0550,-118.2480
"""

CSV_SHOCK_BREACH_AFTER_HANDOVER = """timestamp,temperature_c,shock_g,latitude,longitude
2026-06-15T10:00:00Z,-18.5,0.2,34.0522,-118.2437
2026-06-15T12:00:00Z,-18.2,0.4,34.0525,-118.2440
2026-06-15T14:00:00Z,-18.0,0.3,34.0530,-118.2445
2026-06-15T16:45:00Z,-17.8,6.8,34.0800,-118.3000
2026-06-15T18:00:00Z,-18.1,0.3,34.1200,-118.4000
"""

CSV_NORMAL_NO_BREACH = """timestamp,temperature_c,shock_g,latitude,longitude
2026-06-15T10:00:00Z,-18.5,0.2,34.0522,-118.2437
2026-06-15T12:00:00Z,-18.2,0.3,34.0525,-118.2440
2026-06-15T14:00:00Z,-18.0,0.4,34.0530,-118.2445
2026-06-15T16:00:00Z,-17.9,0.2,34.0550,-118.2480
"""


def get_mock_eir_handover_at_1400_utc(condition=HandoverCondition.CLEAN) -> ExtractedEIRData:
    return ExtractedEIRData(
        carrier_name="Apex Drayage LLC",
        releasing_entity="Origin Shipper Inc.",
        receiving_entity="Apex Drayage LLC",
        container_id="MSKU9082345",
        gate_event_type=GateEventType.INGATE,
        raw_timestamp_str="2026-06-15T14:00:00Z",
        extracted_timezone_str="UTC",
        facility_location="Apex Logistics Yard Los Angeles",
        condition_summary=condition,
        field_evidence_map={
            "container_id": FieldEvidence(
                field_name="container_id",
                extracted_value="MSKU9082345",
                verbatim_quote="CONTAINER NO: MSKU9082345",
                is_verified=True
            ),
            "raw_timestamp_str": FieldEvidence(
                field_name="raw_timestamp_str",
                extracted_value="2026-06-15T14:00:00Z",
                verbatim_quote="GATE HANDOVER: 2026-06-15T14:00:00Z",
                is_verified=True
            )
        }
    )


# ==============================================================================
# 1. CRITICAL ACCEPTANCE TESTS: BEFORE VS. AFTER HANDOVER SHIFT
# ==============================================================================

def test_breach_before_carrier_handoff_attributes_shipper():
    """
    When telemetry temperature excursion begins at 11:30 UTC and carrier handoff
    occurs at 14:00 UTC, responsibility is deterministically attributed to Origin Shipper.
    """
    case_meta = CaseDisputeMetadata(
        shipment_id="DISP-BEFORE-001",
        shipper_name="Origin Shipper Inc.",
        carrier_name="Apex Drayage LLC",
        commodity="Frozen Pharma Vaccine",
        declared_value_usd=120000.0
    )
    eir = get_mock_eir_handover_at_1400_utc()
    thresholds = TelemetryThresholdConfig(temp_max_c=4.0)

    service = DisputeInvestigationService()
    request = DisputeInvestigationRequest(
        case_metadata=case_meta,
        telemetry_csv=CSV_TEMP_BREACH_BEFORE_HANDOVER,
        thresholds=thresholds,
        pre_extracted_eir=eir
    )

    response = service.process_investigation(request)
    assessment = response.evidence_backed_assessment
    overlap = response.deterministic_overlap

    # Assert Deterministic Overlap Anchor
    assert overlap.has_breach is True
    assert overlap.culpable_party == "Origin Shipper Inc."
    assert overlap.culpable_role == CustodyRole.SHIPPER
    assert overlap.earliest_breach_timestamp_utc == datetime(2026, 6, 15, 11, 30, 0, tzinfo=timezone.utc)
    assert "BEFORE carrier custody handover" in overlap.basis_reasoning

    # Assert Evidence-Backed Assessment
    assert assessment.potentially_responsible_party == "Origin Shipper Inc."
    assert assessment.potentially_responsible_role == CustodyRole.SHIPPER
    assert len(assessment.supporting_evidence) > 0


def test_breach_after_carrier_handoff_attributes_carrier():
    """
    When telemetry 6.8G impact shock occurs at 16:45 UTC and carrier handoff
    occurred at 14:00 UTC, responsibility is deterministically attributed to Apex Drayage LLC.
    """
    case_meta = CaseDisputeMetadata(
        shipment_id="DISP-AFTER-002",
        shipper_name="Origin Shipper Inc.",
        carrier_name="Apex Drayage LLC",
        commodity="Precision Optical Equipment",
        declared_value_usd=85000.0
    )
    eir = get_mock_eir_handover_at_1400_utc()
    thresholds = TelemetryThresholdConfig(shock_g_threshold=4.0)

    service = DisputeInvestigationService()
    request = DisputeInvestigationRequest(
        case_metadata=case_meta,
        telemetry_csv=CSV_SHOCK_BREACH_AFTER_HANDOVER,
        thresholds=thresholds,
        pre_extracted_eir=eir
    )

    response = service.process_investigation(request)
    assessment = response.evidence_backed_assessment
    overlap = response.deterministic_overlap

    # Assert Deterministic Overlap Anchor
    assert overlap.has_breach is True
    assert overlap.culpable_party == "Apex Drayage LLC"
    assert overlap.culpable_role == CustodyRole.DRAYAGE_ORIGIN
    assert overlap.earliest_breach_timestamp_utc == datetime(2026, 6, 15, 16, 45, 0, tzinfo=timezone.utc)
    assert "AFTER carrier custody handover" in overlap.basis_reasoning

    # Assert Evidence-Backed Assessment
    assert assessment.potentially_responsible_party == "Apex Drayage LLC"
    assert assessment.potentially_responsible_role == CustodyRole.DRAYAGE_ORIGIN


def test_responsibility_dynamically_changes_based_on_timing():
    """
    Directly asserts that changing breach timestamp relative to handover alters culpable party.
    """
    case_meta = CaseDisputeMetadata(
        shipper_name="Origin Shipper Inc.",
        carrier_name="Apex Drayage LLC"
    )
    eir = get_mock_eir_handover_at_1400_utc()

    # Before handoff
    tel_before = DeterministicTelemetryEngine.process_csv(
        CSV_TEMP_BREACH_BEFORE_HANDOVER,
        thresholds=TelemetryThresholdConfig(temp_max_c=4.0)
    )
    _, _, overlap_before = DeterministicTimelineFusionEngine.fuse_timeline(
        tel_before, eir, case_meta
    )
    assert overlap_before.culpable_party == "Origin Shipper Inc."

    # After handoff
    tel_after = DeterministicTelemetryEngine.process_csv(
        CSV_SHOCK_BREACH_AFTER_HANDOVER,
        thresholds=TelemetryThresholdConfig(shock_g_threshold=4.0)
    )
    _, _, overlap_after = DeterministicTimelineFusionEngine.fuse_timeline(
        tel_after, eir, case_meta
    )
    assert overlap_after.culpable_party == "Apex Drayage LLC"


# ==============================================================================
# 2. TIMEZONE MISMATCH AND NORMALIZATION
# ==============================================================================

def test_timezone_mismatch_normalized_cleanly():
    """
    EIR has timestamp in EDT (2026-06-15 10:00:00 EDT -> 14:00:00 UTC),
    telemetry in UTC. Overlap is computed accurately without offset errors.
    """
    case_meta = CaseDisputeMetadata(
        shipper_name="Origin Shipper Inc.",
        carrier_name="Apex Drayage LLC"
    )
    eir = ExtractedEIRData(
        carrier_name="Apex Drayage LLC",
        releasing_entity="Origin Shipper Inc.",
        receiving_entity="Apex Drayage LLC",
        container_id="MSKU9082345",
        raw_timestamp_str="2026-06-15 10:00:00 EDT",  # 14:00 UTC
        extracted_timezone_str="EDT",
        condition_summary=HandoverCondition.CLEAN
    )

    tel = DeterministicTelemetryEngine.process_csv(
        CSV_SHOCK_BREACH_AFTER_HANDOVER,
        thresholds=TelemetryThresholdConfig(shock_g_threshold=4.0)
    )
    events, windows, overlap = DeterministicTimelineFusionEngine.fuse_timeline(
        tel, eir, case_meta
    )

    # 16:45 UTC shock is 2h45m after 10:00 EDT (14:00 UTC)
    assert overlap.culpable_party == "Apex Drayage LLC"
    assert overlap.earliest_breach_timestamp_utc == datetime(2026, 6, 15, 16, 45, 0, tzinfo=timezone.utc)


# ==============================================================================
# 3. CONFLICTING EVIDENCE HANDLING
# ==============================================================================

def test_conflicting_evidence_captured():
    """
    EIR condition is marked CLEAN, but telemetry records 6.8G impact.
    Conflicting evidence is captured in the assessment.
    """
    case_meta = CaseDisputeMetadata(
        shipper_name="Origin Shipper Inc.",
        carrier_name="Apex Drayage LLC"
    )
    eir = get_mock_eir_handover_at_1400_utc(condition=HandoverCondition.CLEAN)
    thresholds = TelemetryThresholdConfig(shock_g_threshold=4.0)

    service = DisputeInvestigationService()
    request = DisputeInvestigationRequest(
        case_metadata=case_meta,
        telemetry_csv=CSV_SHOCK_BREACH_AFTER_HANDOVER,
        thresholds=thresholds,
        pre_extracted_eir=eir
    )

    response = service.process_investigation(request)
    assessment = response.evidence_backed_assessment

    assert len(assessment.conflicting_evidence) > 0
    conflict = assessment.conflicting_evidence[0]
    assert "CLEAN" in conflict.verbatim_quote_or_datapoint


# ==============================================================================
# 4. UNREADABLE EIR, MISSING TELEMETRY, AND MISSING TIMESTAMPS
# ==============================================================================

def test_missing_telemetry_breaches():
    """
    When telemetry has no breaches, assessment reports no breach and advises further investigation.
    """
    case_meta = CaseDisputeMetadata()
    eir = get_mock_eir_handover_at_1400_utc()
    thresholds = TelemetryThresholdConfig(temp_max_c=4.0, shock_g_threshold=4.0)

    service = DisputeInvestigationService()
    request = DisputeInvestigationRequest(
        case_metadata=case_meta,
        telemetry_csv=CSV_NORMAL_NO_BREACH,
        thresholds=thresholds,
        pre_extracted_eir=eir
    )

    response = service.process_investigation(request)
    overlap = response.deterministic_overlap
    assessment = response.evidence_backed_assessment

    assert overlap.has_breach is False
    assert overlap.culpable_party is None
    assert "No sensor threshold breaches" in overlap.basis_reasoning


def test_missing_handoff_timestamp_flags_uncertainty():
    """
    When EIR timestamp is missing, overlap confidence is downgraded and uncertainty flagged.
    """
    case_meta = CaseDisputeMetadata(
        shipper_name="Origin Shipper Inc.",
        carrier_name="Apex Drayage LLC"
    )
    eir = ExtractedEIRData(
        carrier_name="Apex Drayage LLC",
        releasing_entity="Origin Shipper Inc.",
        receiving_entity="Apex Drayage LLC",
        container_id="MSKU9082345",
        raw_timestamp_str=None,  # Missing timestamp!
        condition_summary=HandoverCondition.CLEAN
    )

    service = DisputeInvestigationService()
    request = DisputeInvestigationRequest(
        case_metadata=case_meta,
        telemetry_csv=CSV_SHOCK_BREACH_AFTER_HANDOVER,
        thresholds=TelemetryThresholdConfig(shock_g_threshold=4.0),
        pre_extracted_eir=eir
    )

    response = service.process_investigation(request)
    overlap = response.deterministic_overlap
    assert overlap.overlap_confidence < 0.60
    assert "EIR handover timestamp was missing" in overlap.basis_reasoning


# ==============================================================================
# 5. LEGAL BOUNDARY AND STATUTORY CITATION COMPLIANCE
# ==============================================================================

def test_legal_boundary_compliance():
    """
    Ensures that outputs never claim to be a 'legal ruling' and include required disclaimers.
    """
    case_meta = CaseDisputeMetadata(governing_regime="Carmack Amendment")
    eir = get_mock_eir_handover_at_1400_utc()
    thresholds = TelemetryThresholdConfig(shock_g_threshold=4.0)

    service = DisputeInvestigationService()
    request = DisputeInvestigationRequest(
        case_metadata=case_meta,
        telemetry_csv=CSV_SHOCK_BREACH_AFTER_HANDOVER,
        thresholds=thresholds,
        pre_extracted_eir=eir
    )

    response = service.process_investigation(request)
    assessment = response.evidence_backed_assessment

    # Disclaimers present
    assert assessment.disclaimer is not None
    assert "does NOT constitute a binding legal ruling" in assessment.disclaimer

    # Forbidden phrases absent
    assessment_str = assessment.model_dump_json()
    assert "Legal ruling" not in assessment_str
    assert "Binding liability determination" not in assessment_str
    assert "Guaranteed legal liability" not in assessment_str

    # Statutory citation present
    assert assessment.applicable_framework.citation == "49 U.S.C. § 14706"


# ==============================================================================
# 6. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_assess_dispute_endpoint(client):
    """Tests POST /api/investigation/assess-dispute JSON endpoint."""
    payload = {
        "case_metadata": {
            "shipment_id": "API-TEST-001",
            "shipper_name": "Pharma Origin Corp",
            "carrier_name": "Apex Drayage LLC",
            "governing_regime": "Carmack Amendment"
        },
        "telemetry_csv": CSV_TEMP_BREACH_BEFORE_HANDOVER,
        "thresholds": {"temp_max_c": 4.0}
    }

    response = client.post("/api/investigation/assess-dispute", json=payload)
    assert response.status_code == 200
    res = response.json()

    assert res["shipment_id"] == "API-TEST-001"
    assert "reconstructed_timeline" in res
    assert "deterministic_overlap" in res
    assert "evidence_backed_assessment" in res
    assert res["deterministic_overlap"]["has_breach"] is True


def test_api_assess_multipart_endpoint(client):
    """Tests POST /api/investigation/assess-multipart endpoint."""
    files = {
        "telemetry_file": ("telemetry.csv", io.BytesIO(CSV_SHOCK_BREACH_AFTER_HANDOVER.encode("utf-8")), "text/csv")
    }
    data = {
        "shipment_id": "MP-TEST-002",
        "shipper_name": "Global Exporter",
        "carrier_name": "Apex Drayage LLC",
        "shock_g_threshold": 4.0
    }

    response = client.post("/api/investigation/assess-multipart", files=files, data=data)
    assert response.status_code == 200
    res = response.json()
    assert res["shipment_id"] == "MP-TEST-002"
    assert res["deterministic_overlap"]["has_breach"] is True


def test_api_fuse_timeline_direct_endpoint(client):
    """Tests POST /api/investigation/fuse-timeline direct timeline endpoint."""
    payload = {
        "case_metadata": {"shipment_id": "TL-FUSE-003"},
        "telemetry_csv": CSV_TEMP_BREACH_BEFORE_HANDOVER,
        "thresholds": {"temp_max_c": 4.0}
    }

    response = client.post("/api/investigation/fuse-timeline", json=payload)
    assert response.status_code == 200
    res = response.json()
    assert res["shipment_id"] == "TL-FUSE-003"
    assert res["timeline_events_count"] > 0
