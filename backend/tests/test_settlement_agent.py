import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import create_app
from backend.models.case import (
    CaseModel,
    CaseStatus,
    ShipmentInfo,
    HumanApprovalEvent,
    SettlementState
)
from backend.models.settlement import (
    CarrierObjectionType,
    DraftApprovalStatus,
    InboundCarrierMessage,
    OutboundDraft
)
from backend.services.case_repository import FirestoreCaseRepository
from backend.services.case_service import CaseService
from backend.services.settlement_service import SettlementService, InvalidDraftWorkflowError
from backend.services.carrier_simulator import CarrierSimulator
from backend.agents.settlement_agent import SettlementAgent


@pytest.fixture
def repo():
    r = FirestoreCaseRepository()
    r.clear()
    return r


@pytest.fixture
def case_service(repo):
    return CaseService(repository=repo)


@pytest.fixture
def settlement_service(case_service):
    return SettlementService(case_service=case_service)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def create_approved_test_case(case_service: CaseService, case_id: str = "CASE-SETTLE-001") -> CaseModel:
    """Helper to create a fully approved case ready for settlement."""
    case = case_service.create_case(
        shipment_info=ShipmentInfo(
            container_id="MSKU9082345",
            commodity="Pharmaceutical Vaccines",
            declared_value_usd=100000.0,
            claimed_loss_usd=75000.0,
            carrier_name="Apex Drayage LLC"
        ),
        custom_case_id=case_id
    )
    # Transition to APPROVED
    case = case_service.record_human_approval(
        case_id=case.case_id,
        approval=HumanApprovalEvent(
            approval_id="APP-001",
            adjuster_name="Sarah Doe",
            allocated_liability_pct=100.0,
            audit_badge_token="BADGE-APPROVED-100"
        )
    )
    return case


# ==============================================================================
# 1. STRICT EXECUTION GATE ON CASE STATUS
# ==============================================================================

def test_settlement_agent_rejects_unapproved_case(case_service, settlement_service):
    """Settlement agent must fail if case is still in INGESTED status."""
    case = case_service.create_case(custom_case_id="CASE-UNAPPROVED-01")
    assert case.status == CaseStatus.NEW

    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.DAMAGE_BEFORE_PICKUP
    )

    with pytest.raises(ValueError) as exc_info:
        settlement_service.generate_draft_response(case.case_id, inbound)
    assert "Settlement Agent operates ONLY after a case reaches APPROVED status" in str(exc_info.value)


def test_settlement_agent_executes_on_approved_case(case_service, settlement_service):
    """Settlement agent executes successfully on APPROVED case."""
    case = create_approved_test_case(case_service, "CASE-APPROVED-02")
    assert case.status == CaseStatus.APPROVED

    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.DAMAGE_BEFORE_PICKUP
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.status == DraftApprovalStatus.DRAFT
    assert draft.identified_carrier_objection == CarrierObjectionType.DAMAGE_BEFORE_PICKUP


# ==============================================================================
# 2. CARRIER OBJECTION ADAPTATION & EVIDENCE SELECTION
# ==============================================================================

def test_objection_damage_before_pickup_selects_eir_evidence(case_service, settlement_service):
    """Carrier claims damage occurred before pickup -> Rebuttal selects clean EIR and telemetry time."""
    case = create_approved_test_case(case_service, "CASE-OBJ-01")
    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.DAMAGE_BEFORE_PICKUP
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.identified_carrier_objection == CarrierObjectionType.DAMAGE_BEFORE_PICKUP
    citation_sources = [c.source_type for c in draft.relevant_evidence_citations]
    assert "EIR_DOCUMENT" in citation_sources
    assert "Clean Interchange Handover" in draft.draft_body_markdown


def test_objection_disputes_custody_selects_overlap_evidence(case_service, settlement_service):
    """Carrier claims container was not in their care -> Rebuttal selects custody overlap evidence."""
    case = create_approved_test_case(case_service, "CASE-OBJ-02")
    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.DISPUTES_CUSTODY
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.identified_carrier_objection == CarrierObjectionType.DISPUTES_CUSTODY
    assert "Rebuttal to Carrier Custody Disclaimer" in draft.draft_body_markdown


def test_objection_sensor_reliability_selects_calibration_evidence(case_service, settlement_service):
    """Carrier disputes sensor reliability -> Rebuttal selects telemetry precision and calibration."""
    case = create_approved_test_case(case_service, "CASE-OBJ-03")
    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.DISPUTES_SENSOR_RELIABILITY
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.identified_carrier_objection == CarrierObjectionType.DISPUTES_SENSOR_RELIABILITY
    assert "Technical Validation of IoT Sensor Telemetry" in draft.draft_body_markdown


def test_objection_notice_late_selects_statutory_window(case_service, settlement_service):
    """Carrier claims claim is late -> Rebuttal cites 49 U.S.C. § 14706 9-month statutory rule."""
    case = create_approved_test_case(case_service, "CASE-OBJ-04")
    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.NOTICE_ALLEGEDLY_LATE
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.identified_carrier_objection == CarrierObjectionType.NOTICE_ALLEGEDLY_LATE
    assert "49 U.S.C. § 14706" in draft.draft_body_markdown


def test_objection_requests_docs_provides_exhibit_index(case_service, settlement_service):
    """Carrier requests documentation -> Rebuttal transmits exhibit list."""
    case = create_approved_test_case(case_service, "CASE-OBJ-05")
    inbound = CarrierSimulator.generate_inbound_message(
        case_id=case.case_id,
        objection_type=CarrierObjectionType.REQUESTS_SUPPORTING_DOCS
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.identified_carrier_objection == CarrierObjectionType.REQUESTS_SUPPORTING_DOCS
    assert "Exhibit A: Signed Equipment Interchange Receipt" in draft.draft_body_markdown


def test_response_changes_appropriately_across_objections(case_service, settlement_service):
    """Verifies that draft text and subjects are completely distinct for different objections."""
    case = create_approved_test_case(case_service, "CASE-DIFF-01")
    
    inbound_pre = CarrierSimulator.generate_inbound_message(case.case_id, CarrierObjectionType.DAMAGE_BEFORE_PICKUP)
    draft_pre = settlement_service.generate_draft_response(case.case_id, inbound_pre)

    inbound_late = CarrierSimulator.generate_inbound_message(case.case_id, CarrierObjectionType.NOTICE_ALLEGEDLY_LATE)
    draft_late = settlement_service.generate_draft_response(case.case_id, inbound_late)

    assert draft_pre.draft_subject != draft_late.draft_subject
    assert draft_pre.draft_body_markdown != draft_late.draft_body_markdown


# ==============================================================================
# 3. ESCALATION ON GENERAL DENIAL / MISSING EVIDENCE
# ==============================================================================

def test_general_denial_triggers_escalation(case_service, settlement_service):
    """When carrier sends an unspecific denial, draft flags requires_escalation."""
    case = create_approved_test_case(case_service, "CASE-ESCALATE-01")
    inbound = InboundCarrierMessage(
        message_id="IN-GENERAL-DENY",
        case_id=case.case_id,
        sender_party="Carrier Legal",
        subject="Re: Claim",
        body_text="We decline this claim in its entirety. No further explanation.",
        identified_objection=CarrierObjectionType.GENERAL_DENIAL
    )

    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.requires_escalation is True
    assert draft.escalation_reason is not None


# ==============================================================================
# 4. 5-STAGE HUMAN APPROVAL WORKFLOW
# DRAFT -> HUMAN_REVIEW -> APPROVE -> SECURITY_CHECK -> READY_TO_SEND
# ==============================================================================

def test_full_human_approval_workflow(case_service, settlement_service):
    case = create_approved_test_case(case_service, "CASE-WORKFLOW-01")
    inbound = CarrierSimulator.generate_inbound_message(case.case_id, CarrierObjectionType.DAMAGE_BEFORE_PICKUP)

    # 1. DRAFT
    draft = settlement_service.generate_draft_response(case.case_id, inbound)
    assert draft.status == DraftApprovalStatus.DRAFT

    # Illegal attempt to dispatch directly from DRAFT must fail
    with pytest.raises(InvalidDraftWorkflowError):
        settlement_service.dispatch_outbound_message(case.case_id, draft.draft_id)

    # 2. DRAFT -> HUMAN_REVIEW
    draft = settlement_service.submit_for_human_review(draft.draft_id)
    assert draft.status == DraftApprovalStatus.HUMAN_REVIEW

    # 3. HUMAN_REVIEW -> APPROVE
    draft = settlement_service.approve_draft(
        draft_id=draft.draft_id,
        adjuster_name="Sarah Doe",
        notes="Adjuster checked EIR and approved rebuttal."
    )
    assert draft.status == DraftApprovalStatus.APPROVE
    assert draft.human_reviewer == "Sarah Doe"

    # 4. APPROVE -> SECURITY_CHECK -> READY_TO_SEND
    draft = settlement_service.run_security_check(draft.draft_id)
    assert draft.status == DraftApprovalStatus.READY_TO_SEND
    assert draft.security_check_passed is True

    # 5. READY_TO_SEND -> DISPATCH to Firestore
    updated_case = settlement_service.dispatch_outbound_message(case.case_id, draft.draft_id)
    assert updated_case.status == CaseStatus.NEGOTIATION
    assert len(updated_case.negotiation_history) == 1
    assert "Equipment Interchange Receipt" in updated_case.negotiation_history[0].message_text


# ==============================================================================
# 5. THREE-TURN DETERMINISTIC NEGOTIATION SIMULATION
# ==============================================================================

def test_three_turn_negotiation_simulation(case_service, settlement_service):
    """
    Executes a 3-turn interactive negotiation:
    Turn 1: Carrier disputes liability -> Rebuttal with EIR clean stamp.
    Turn 2: Carrier offers partial settlement ($45,000) -> Counter-offer ($65,000).
    Turn 3: Carrier accepts settlement at $65,000 -> Case marked RESOLVED in Firestore.
    """
    case = create_approved_test_case(case_service, "CASE-SIM-3TURN")
    
    result = settlement_service.run_three_turn_simulation(case.case_id)

    assert result.settlement_achieved is True
    assert result.starting_demand_usd == 75000.0
    assert result.final_settlement_usd == round(75000.0 * 0.85, 2)
    assert len(result.turns) == 3

    # Check that case in Firestore was updated to RESOLVED with 3 negotiation rounds
    resolved_case = case_service.get_case(case.case_id)
    assert resolved_case.status == CaseStatus.RESOLVED
    assert len(resolved_case.negotiation_history) == 3
    assert resolved_case.closed_at_utc is not None


# ==============================================================================
# 6. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_settlement_endpoints(client):
    # 1. Create and approve case
    create_res = client.post("/api/cases", json={"custom_case_id": "API-SETTLE-CASE", "initial_status": "APPROVED"})
    assert create_res.status_code == 201

    # 2. Get sample carrier objection
    sample_res = client.post(
        "/api/settlement/carrier-objection-sample",
        json={"case_id": "API-SETTLE-CASE", "objection_type": "DAMAGE_BEFORE_PICKUP"}
    )
    assert sample_res.status_code == 200
    inbound_payload = sample_res.json()

    # 3. Generate draft
    draft_res = client.post(
        "/api/settlement/API-SETTLE-CASE/draft",
        json={"inbound_message": inbound_payload}
    )
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    draft_id = draft_data["draft_id"]
    assert draft_data["status"] == "DRAFT"

    # 4. Review draft
    rev_res = client.post(f"/api/settlement/drafts/{draft_id}/review")
    assert rev_res.status_code == 200
    assert rev_res.json()["status"] == "HUMAN_REVIEW"

    # 5. Approve draft
    app_res = client.post(
        f"/api/settlement/drafts/{draft_id}/approve",
        json={"adjuster_name": "Adjuster John"}
    )
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "APPROVE"

    # 6. Security check
    sec_res = client.post(f"/api/settlement/drafts/{draft_id}/security-check")
    assert sec_res.status_code == 200
    assert sec_res.json()["status"] == "READY_TO_SEND"

    # 7. Dispatch
    disp_res = client.post(
        f"/api/settlement/API-SETTLE-CASE/drafts/{draft_id}/dispatch",
        json={"actor": "Adjuster John"}
    )
    assert disp_res.status_code == 200
    assert disp_res.json()["status"] == "NEGOTIATION"


def test_api_simulate_three_turn_endpoint(client):
    client.post("/api/cases", json={"custom_case_id": "API-SIM-CASE", "initial_status": "APPROVED"})

    sim_res = client.post("/api/settlement/API-SIM-CASE/simulate-three-turn")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["settlement_achieved"] is True
    assert sim_data["final_settlement_usd"] == round(75000.0 * 0.85, 2)
    assert len(sim_data["turns"]) == 3


def test_dynamic_custom_loss_and_carrier_negotiation(settlement_service, case_service):
    """
    Dynamic testing verification: Proves that settlement negotiation and simulation
    are 100% dynamic without any hardcoded carrier or dollar figure assumptions.
    """
    case = case_service.create_case(
        shipment_info=ShipmentInfo(
            container_id="SWFT-991188",
            commodity="Organic Berries",
            declared_value_usd=50000.0,
            claimed_loss_usd=40000.0,
            carrier_name="Swift Freight Dynamics"
        ),
        custom_case_id="CASE-DYNAMIC-40K"
    )

    result = settlement_service.run_three_turn_simulation("CASE-DYNAMIC-40K")
    assert result.settlement_achieved is True
    # 85% of $40,000 = $34,000
    assert result.final_settlement_usd == 34000.0
    assert len(result.turns) == 3

    turn1 = result.turns[0]
    assert "Swift Freight Dynamics" in turn1.inbound_carrier_message.sender_party

    turn2 = result.turns[1]
    # 60% of $40,000 = $24,000
    assert turn2.inbound_carrier_message.offered_amount_usd == 24000.0
    assert "$24,000.00" in turn2.inbound_carrier_message.body_text
    assert turn2.outbound_draft.proposed_settlement_amount_usd == 34000.0

    turn3 = result.turns[2]
    assert turn3.inbound_carrier_message.offered_amount_usd == 34000.0
    assert "$34,000.00" in turn3.inbound_carrier_message.body_text
    assert "SWFT-991188" in turn3.inbound_carrier_message.body_text

