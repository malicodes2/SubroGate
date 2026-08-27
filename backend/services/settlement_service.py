import uuid
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..models.case import CaseModel, CaseStatus, NegotiationMessage, SettlementState, HumanApprovalEvent
from ..models.settlement import (
    CarrierObjectionType,
    DraftApprovalStatus,
    InboundCarrierMessage,
    OutboundDraft,
    SimulationTurn,
    ThreeTurnNegotiationResult
)
from ..models.security import SecurityVerdict, SecurityScreeningReport
from ..agents.settlement_agent import SettlementAgent
from .case_service import CaseService
from .carrier_simulator import CarrierSimulator
from .security_service import SecurityScreeningService
from ..observability.tracer import trace_span


class DraftNotFoundError(Exception):
    """Raised when an outbound draft is not found."""
    pass


class InvalidDraftWorkflowError(Exception):
    """Raised when an illegal draft state progression is attempted."""
    pass


class SettlementService:
    """
    Orchestration service for the Settlement Agent, security screening gate,
    outbound draft approval, and negotiation persistence.
    """

    def __init__(
        self,
        case_service: Optional[CaseService] = None,
        settlement_agent: Optional[SettlementAgent] = None,
        security_service: Optional[SecurityScreeningService] = None
    ):
        self.case_service = case_service or CaseService()
        self.agent = settlement_agent or SettlementAgent()
        self.security_service = security_service or SecurityScreeningService(case_service=self.case_service)
        self._drafts_store: Dict[str, OutboundDraft] = {}

    def generate_draft_response(
        self,
        case_id: str,
        inbound_message: InboundCarrierMessage,
        actor: str = "SETTLEMENT_AGENT"
    ) -> OutboundDraft:
        """
        Invokes Settlement Agent to analyze carrier response, generates DRAFT,
        and immediately routes through the Security Screening Gate.
        """
        with trace_span(
            name="Settlement Agent Rebuttal Generation",
            case_id=case_id,
            category="SETTLEMENT_AGENT",
            attributes={"inbound.objection": inbound_message.identified_objection.value if inbound_message.identified_objection else "UNKNOWN"}
        ) as span:
            case = self.case_service.get_case(case_id)
            if not case:
                raise ValueError(f"Case with ID '{case_id}' not found.")

            # 1. Agent generates initial DRAFT
            draft = self.agent.analyze_carrier_response_and_draft(case, inbound_message)
            
            # 2. Security Screening Gate (Google Model Armor / Local Fallback)
            report = self.security_service.screen_draft(draft, case_id=case_id)
            draft.security_report = report.model_dump(mode="json")

            # 3. Route status according to Security Verdict
            if report.verdict == SecurityVerdict.PASS:
                draft.status = DraftApprovalStatus.DRAFT
            elif report.verdict == SecurityVerdict.REVIEW:
                draft.status = DraftApprovalStatus.SECURITY_REVIEW
            else:
                draft.status = DraftApprovalStatus.SECURITY_BLOCKED

            self._drafts_store[draft.draft_id] = draft

            # Append audit event to case
            self.case_service.append_audit_event(
                case_id=case_id,
                event_type="SETTLEMENT_DRAFT_GENERATED",
                description=(
                    f"Settlement Agent generated outbound draft '{draft.draft_id}' (Objection: {draft.identified_carrier_objection.value}). "
                    f"Security Verdict: '{report.verdict.value}'."
                ),
                actor=actor,
                metadata={
                    "draft_id": draft.draft_id,
                    "objection": draft.identified_carrier_objection.value,
                    "security_verdict": report.verdict.value,
                    "findings_count": report.findings_count
                }
            )

            span.set_attribute("draft_id", draft.draft_id)
            span.set_attribute("security_verdict", report.verdict.value)

            return draft

    def get_draft(self, draft_id: str) -> Optional[OutboundDraft]:
        return self._drafts_store.get(draft_id)

    # ==========================================================================
    # SECURITY & SANITIZATION ACTIONS
    # ==========================================================================

    def apply_sanitization(self, draft_id: str, actor: str = "ADJUSTER") -> OutboundDraft:
        """
        Applies the suggested sanitized version to the draft upon human adjuster confirmation.
        Re-screens the text to ensure all sensitive tokens are resolved.
        """
        draft = self._drafts_store.get(draft_id)
        if not draft:
            raise DraftNotFoundError(f"Draft '{draft_id}' not found.")

        if not draft.security_report or "suggested_sanitization" not in draft.security_report:
            raise ValueError(f"No security sanitization report available for draft '{draft_id}'.")

        # Apply suggested sanitized text
        sanitized = draft.security_report["suggested_sanitization"]
        draft.draft_body_markdown = sanitized

        # Re-screen sanitized text
        report = self.security_service.screen_draft(draft, case_id=draft.case_id, actor=actor)
        draft.security_report = report.model_dump(mode="json")

        if report.verdict == SecurityVerdict.PASS:
            draft.status = DraftApprovalStatus.HUMAN_REVIEW
        else:
            draft.status = DraftApprovalStatus.SECURITY_REVIEW

        return draft

    def submit_for_human_review(self, draft_id: str, actor: str = "USER") -> OutboundDraft:
        """Submits/advances draft to HUMAN_REVIEW."""
        draft = self._drafts_store.get(draft_id)
        if not draft:
            raise DraftNotFoundError(f"Draft '{draft_id}' not found.")

        if draft.status == DraftApprovalStatus.SECURITY_BLOCKED:
            raise InvalidDraftWorkflowError("Cannot submit draft in SECURITY_BLOCKED state for approval without resolving security violation.")

        draft.status = DraftApprovalStatus.HUMAN_REVIEW
        draft.reviewed_at_utc = datetime.now(timezone.utc)
        return draft

    def approve_draft(
        self,
        draft_id: str,
        adjuster_name: str,
        notes: Optional[str] = None
    ) -> OutboundDraft:
        """
        Adjuster reviews and approves the draft.
        Blocks approval if draft remains in SECURITY_BLOCKED state.
        """
        draft = self._drafts_store.get(draft_id)
        if not draft:
            raise DraftNotFoundError(f"Draft '{draft_id}' not found.")

        if draft.status == DraftApprovalStatus.SECURITY_BLOCKED:
            raise InvalidDraftWorkflowError("Cannot approve draft in SECURITY_BLOCKED status. Resolve critical security findings first.")

        if draft.status not in (DraftApprovalStatus.HUMAN_REVIEW, DraftApprovalStatus.SECURITY_REVIEW, DraftApprovalStatus.DRAFT):
            raise InvalidDraftWorkflowError(f"Draft must be in review state to approve. Current: '{draft.status.value}'.")

        draft.status = DraftApprovalStatus.APPROVE
        draft.human_reviewer = adjuster_name
        draft.adjuster_modifications_notes = notes
        draft.approved_at_utc = datetime.now(timezone.utc)
        return draft

    def run_security_check(self, draft_id: str) -> OutboundDraft:
        """
        Final pre-dispatch verification advancing approved draft to READY_TO_SEND.
        """
        draft = self._drafts_store.get(draft_id)
        if not draft:
            raise DraftNotFoundError(f"Draft '{draft_id}' not found.")

        if draft.status != DraftApprovalStatus.APPROVE:
            raise InvalidDraftWorkflowError(f"Draft must be in APPROVE state before final security validation. Current: '{draft.status.value}'.")

        report = self.security_service.screen_draft(draft, case_id=draft.case_id)
        draft.security_report = report.model_dump(mode="json")

        if report.verdict == SecurityVerdict.BLOCK:
            draft.status = DraftApprovalStatus.SECURITY_BLOCKED
            raise ValueError("Pre-dispatch security check failed: Critical security risk or prompt injection detected.")

        draft.security_check_passed = True
        draft.status = DraftApprovalStatus.READY_TO_SEND
        return draft

    def dispatch_outbound_message(
        self,
        case_id: str,
        draft_id: str,
        actor: str = "ADJUSTER"
    ) -> CaseModel:
        """
        Final Stage: Dispatches READY_TO_SEND draft to case negotiation history in Firestore.
        """
        draft = self._drafts_store.get(draft_id)
        if not draft:
            raise DraftNotFoundError(f"Draft '{draft_id}' not found.")

        if draft.status != DraftApprovalStatus.READY_TO_SEND:
            raise InvalidDraftWorkflowError(
                f"Cannot dispatch draft '{draft_id}'. Draft must reach READY_TO_SEND status. Current: '{draft.status.value}'."
            )

        # Convert draft into NegotiationMessage
        message = NegotiationMessage(
            message_id=f"MSG-{uuid.uuid4().hex[:6].upper()}",
            timestamp_utc=datetime.now(timezone.utc),
            sender_party="SubroGate Claims Adjuster",
            recipient_party="Carrier Claims Dept",
            message_type="FORMAL_REBUTTAL",
            message_text=draft.draft_body_markdown,
            proposed_amount_usd=draft.proposed_settlement_amount_usd
        )

        updated_case = self.case_service.append_negotiation_message(
            case_id=case_id,
            message=message,
            actor=actor
        )

        return updated_case

    # ==========================================================================
    # 3-TURN DETERMINISTIC NEGOTIATION SIMULATION
    # ==========================================================================

    def run_three_turn_simulation(self, case_id: str) -> ThreeTurnNegotiationResult:
        """
        Executes a 3-turn interactive subrogation negotiation with complete Firestore persistence
        and security screening gates on each turn.
        """
        case = self.case_service.get_case(case_id)
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        # Ensure case has approval
        if case.status != CaseStatus.APPROVED and case.status != CaseStatus.NEGOTIATION:
            self.case_service.record_human_approval(
                case_id=case_id,
                approval=HumanApprovalEvent(
                    approval_id=f"APP-{uuid.uuid4().hex[:4]}",
                    adjuster_name="Senior Adjuster Sarah",
                    allocated_liability_pct=100.0,
                    audit_badge_token="SIM-AUTH-BADGE"
                )
            )

        turns: List[SimulationTurn] = []
        sim_id = f"SIM-{uuid.uuid4().hex[:6].upper()}"

        # Dynamic case parameters
        claimed_loss = float(case.shipment_info.claimed_loss_usd) if (case.shipment_info and case.shipment_info.claimed_loss_usd) else 75000.0
        carrier_name = case.shipment_info.carrier_name if (case.shipment_info and case.shipment_info.carrier_name) else "Motor Carrier"
        container_id = case.shipment_info.container_id if (case.shipment_info and case.shipment_info.container_id) else "Container"

        offer_amount = round(claimed_loss * 0.60, 2)
        counter_amount = round(claimed_loss * 0.85, 2)

        # ----------------------------------------------------------------------
        # TURN 1: Carrier says "Damage occurred before pickup"
        # ----------------------------------------------------------------------
        inbound_1 = CarrierSimulator.generate_inbound_message(
            case_id=case_id,
            objection_type=CarrierObjectionType.DAMAGE_BEFORE_PICKUP,
            carrier_name=carrier_name
        )
        draft_1 = self.generate_draft_response(case_id, inbound_1)
        self.approve_draft(draft_1.draft_id, "Senior Adjuster Sarah", "Approved with EIR clean stamp evidence.")
        self.run_security_check(draft_1.draft_id)
        self.dispatch_outbound_message(case_id, draft_1.draft_id)

        turns.append(
            SimulationTurn(
                turn_index=1,
                inbound_carrier_message=inbound_1,
                outbound_draft=draft_1,
                status_at_turn_end=DraftApprovalStatus.READY_TO_SEND,
                notes="Turn 1: Rebutted carrier pre-pickup damage defense using signed EIR and telemetry timestamp."
            )
        )

        # ----------------------------------------------------------------------
        # TURN 2: Carrier offers compromise payment (60% of claim)
        # ----------------------------------------------------------------------
        inbound_2 = CarrierSimulator.generate_inbound_message(
            case_id=case_id,
            objection_type=CarrierObjectionType.PARTIAL_SETTLEMENT_OFFER,
            carrier_name=carrier_name,
            offered_amount_usd=offer_amount
        )
        draft_2 = self.generate_draft_response(case_id, inbound_2)
        draft_2.proposed_settlement_amount_usd = counter_amount  # Counter-offer
        self.approve_draft(draft_2.draft_id, "Senior Adjuster Sarah", f"Authorized ${counter_amount:,.2f} compromise counter-offer.")
        self.run_security_check(draft_2.draft_id)
        self.dispatch_outbound_message(case_id, draft_2.draft_id)

        turns.append(
            SimulationTurn(
                turn_index=2,
                inbound_carrier_message=inbound_2,
                outbound_draft=draft_2,
                status_at_turn_end=DraftApprovalStatus.READY_TO_SEND,
                notes=f"Turn 2: Counter-offered ${counter_amount:,.2f} USD above floor."
            )
        )

        # ----------------------------------------------------------------------
        # TURN 3: Carrier accepts final settlement figure (85% of claim)
        # ----------------------------------------------------------------------
        inbound_3 = InboundCarrierMessage(
            message_id=f"IN-MSG-ACCEPT-{uuid.uuid4().hex[:4]}",
            case_id=case_id,
            sender_party=f"{carrier_name} Legal Claims",
            subject=f"RE: Final Settlement Agreement Authorization - ${counter_amount:,.2f} USD",
            body_text=(
                f"Our executive claims committee has agreed to your counter-offer of ${counter_amount:,.2f} USD in full and "
                f"final settlement of all claims regarding container {container_id}. Please send the final release."
            ),
            offered_amount_usd=counter_amount,
            identified_objection=CarrierObjectionType.PARTIAL_SETTLEMENT_OFFER
        )
        draft_3 = self.generate_draft_response(case_id, inbound_3)
        self.approve_draft(draft_3.draft_id, "Senior Adjuster Sarah", "Accepted final settlement agreement.")
        self.run_security_check(draft_3.draft_id)
        self.dispatch_outbound_message(case_id, draft_3.draft_id)

        # Transition Case to RESOLVED
        self.case_service.transition_status(
            case_id=case_id,
            new_status=CaseStatus.RESOLVED,
            actor="SETTLEMENT_AGENT",
            reason=f"Subrogation claim resolved with carrier agreement at ${counter_amount:,.2f} USD."
        )

        turns.append(
            SimulationTurn(
                turn_index=3,
                inbound_carrier_message=inbound_3,
                outbound_draft=draft_3,
                status_at_turn_end=DraftApprovalStatus.READY_TO_SEND,
                notes=f"Turn 3: Settlement finalized at ${counter_amount:,.2f} USD. Case marked RESOLVED."
            )
        )

        return ThreeTurnNegotiationResult(
            simulation_id=sim_id,
            case_id=case_id,
            starting_demand_usd=claimed_loss,
            final_settlement_usd=counter_amount,
            settlement_achieved=True,
            turns=turns
        )
