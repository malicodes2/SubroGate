from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Body, Query, Depends
from pydantic import BaseModel, Field

from ..models.settlement import (
    CarrierObjectionType,
    DraftApprovalStatus,
    InboundCarrierMessage,
    OutboundDraft,
    ThreeTurnNegotiationResult
)
from ..models.case import CaseModel
from ..services.settlement_service import SettlementService, DraftNotFoundError, InvalidDraftWorkflowError
from ..services.carrier_simulator import CarrierSimulator
from ..utils.auth import verify_agent_identity

router = APIRouter(prefix="/api/settlement", tags=["Settlement Agent & Negotiation"])
_settlement_service = SettlementService()


class GenerateDraftRequest(BaseModel):
    inbound_message: InboundCarrierMessage
    actor: str = "SETTLEMENT_AGENT"


class ApproveDraftRequest(BaseModel):
    adjuster_name: str
    notes: Optional[str] = None


class DispatchDraftRequest(BaseModel):
    actor: str = "ADJUSTER"


class GenerateObjectionRequest(BaseModel):
    case_id: str
    objection_type: CarrierObjectionType
    carrier_name: str = "Apex Drayage LLC"
    offered_amount_usd: Optional[float] = None


@router.post("/carrier-objection-sample", response_model=InboundCarrierMessage)
def generate_sample_carrier_objection(payload: GenerateObjectionRequest) -> InboundCarrierMessage:
    """
    Generates a deterministic sample carrier objection letter for testing and live demonstrations.
    """
    return CarrierSimulator.generate_inbound_message(
        case_id=payload.case_id,
        objection_type=payload.objection_type,
        carrier_name=payload.carrier_name,
        offered_amount_usd=payload.offered_amount_usd
    )


@router.post("/{case_id}/draft", response_model=OutboundDraft, dependencies=[Depends(verify_agent_identity)])
def generate_settlement_draft(
    case_id: str,
    payload: GenerateDraftRequest
) -> OutboundDraft:
    """
    Invokes the Settlement Agent to analyze an inbound carrier letter and formulate a factual rebuttal draft.
    Requires case to be in APPROVED or NEGOTIATION status.
    """
    try:
        return _settlement_service.generate_draft_response(
            case_id=case_id,
            inbound_message=payload.inbound_message,
            actor=payload.actor
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/drafts/{draft_id}", response_model=OutboundDraft)
def get_settlement_draft(draft_id: str) -> OutboundDraft:
    """Retrieves an outbound draft by ID."""
    draft = _settlement_service.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft '{draft_id}' not found.")
    return draft


@router.post("/drafts/{draft_id}/apply-sanitization", response_model=OutboundDraft, dependencies=[Depends(verify_agent_identity)])
def apply_draft_sanitization(draft_id: str) -> OutboundDraft:
    """
    Applies the suggested sanitized version to the draft, replacing flagged PII / pricing / margins.
    """
    try:
        return _settlement_service.apply_sanitization(draft_id)
    except (DraftNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/review", response_model=OutboundDraft, dependencies=[Depends(verify_agent_identity)])
def submit_draft_for_review(draft_id: str) -> OutboundDraft:
    """
    Submits DRAFT for HUMAN_REVIEW.
    """
    try:
        return _settlement_service.submit_for_human_review(draft_id)
    except (DraftNotFoundError, InvalidDraftWorkflowError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/approve", response_model=OutboundDraft, dependencies=[Depends(verify_agent_identity)])
def approve_draft_by_adjuster(
    draft_id: str,
    payload: ApproveDraftRequest
) -> OutboundDraft:
    """
    Stage 2 -> Stage 3: Human claims adjuster reviews and APPROVES the draft.
    """
    try:
        return _settlement_service.approve_draft(
            draft_id=draft_id,
            adjuster_name=payload.adjuster_name,
            notes=payload.notes
        )
    except (DraftNotFoundError, InvalidDraftWorkflowError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/drafts/{draft_id}/security-check", response_model=OutboundDraft, dependencies=[Depends(verify_agent_identity)])
def run_draft_security_check(draft_id: str) -> OutboundDraft:
    """
    Stage 3 -> Stage 4 -> Stage 5: Executes automated PII and leak validation, advancing to READY_TO_SEND.
    """
    try:
        return _settlement_service.run_security_check(draft_id)
    except (DraftNotFoundError, InvalidDraftWorkflowError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/drafts/{draft_id}/dispatch", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def dispatch_draft_to_carrier(
    case_id: str,
    draft_id: str,
    payload: DispatchDraftRequest
) -> CaseModel:
    """
    Stage 5 Final: Dispatches READY_TO_SEND draft to case negotiation history in Firestore.
    """
    try:
        return _settlement_service.dispatch_outbound_message(
            case_id=case_id,
            draft_id=draft_id,
            actor=payload.actor
        )
    except (DraftNotFoundError, InvalidDraftWorkflowError) as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{case_id}/simulate-three-turn", response_model=ThreeTurnNegotiationResult, dependencies=[Depends(verify_agent_identity)])
def simulate_three_turn_negotiation(case_id: str) -> ThreeTurnNegotiationResult:
    """
    Executes a complete 3-turn interactive negotiation simulation with Firestore state tracking.
    """
    try:
        return _settlement_service.run_three_turn_simulation(case_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
