from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .investigation import EvidenceCitation, LegalFrameworkReference


class CarrierObjectionType(str, Enum):
    """Standard categorized defenses and objections raised by freight carriers."""
    NOTICE_ALLEGEDLY_LATE = "NOTICE_ALLEGEDLY_LATE"
    DISPUTES_CUSTODY = "DISPUTES_CUSTODY"
    DISPUTES_SENSOR_RELIABILITY = "DISPUTES_SENSOR_RELIABILITY"
    DAMAGE_BEFORE_PICKUP = "DAMAGE_BEFORE_PICKUP"
    REQUESTS_SUPPORTING_DOCS = "REQUESTS_SUPPORTING_DOCS"
    PARTIAL_SETTLEMENT_OFFER = "PARTIAL_SETTLEMENT_OFFER"
    GENERAL_DENIAL = "GENERAL_DENIAL"


class DraftApprovalStatus(str, Enum):
    """Mandatory approval and security lifecycle for outbound carrier communications."""
    DRAFT = "DRAFT"
    SECURITY_REVIEW = "SECURITY_REVIEW"      # Sensitive info detected, adjuster review required
    SECURITY_BLOCKED = "SECURITY_BLOCKED"    # Critical security issue (prompt injection, active secrets)
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVE = "APPROVE"
    SECURITY_CHECK = "SECURITY_CHECK"
    READY_TO_SEND = "READY_TO_SEND"


class InboundCarrierMessage(BaseModel):
    """Structured representation of an incoming letter or email from a carrier claims department."""
    message_id: str = Field(..., description="Unique inbound message identifier (e.g. IN-MSG-001)")
    case_id: str = Field(..., description="Target dispute Case ID")
    sender_party: str = Field(..., description="Carrier name or claims representative (e.g. 'Apex Drayage Claims Dept')")
    sender_email: Optional[str] = Field(None, description="Sender email address")
    subject: str = Field(..., description="Subject line of communication")
    body_text: str = Field(..., description="Raw text of carrier letter or email")
    offered_amount_usd: Optional[float] = Field(None, description="Proposed settlement amount if offer is made")
    identified_objection: Optional[CarrierObjectionType] = Field(None, description="Categorized objection type")
    received_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of receipt")


class OutboundDraft(BaseModel):
    """
    Structured outbound response or counter-demand drafted by the Settlement Agent.
    Must strictly traverse the security screening and human approval workflow before dispatch.
    """
    draft_id: str = Field(..., description="Unique draft identifier (e.g. DRAFT-001)")
    case_id: str = Field(..., description="Associated case identifier")
    in_response_to_message_id: Optional[str] = Field(None, description="ID of inbound carrier message being rebutted")
    
    # Forensic Grounding
    identified_carrier_objection: CarrierObjectionType = Field(..., description="Classified carrier defense being addressed")
    relevant_evidence_citations: List[EvidenceCitation] = Field(default_factory=list, description="Specific factual evidence used to rebut the objection")
    
    # Draft Content
    draft_subject: str = Field(..., description="Proposed formal subject line")
    draft_body_markdown: str = Field(..., description="Draft formal notice / rebuttal in Markdown")
    proposed_settlement_amount_usd: Optional[float] = Field(None, description="Demanded or agreed settlement sum")
    
    # Security Gate Screening
    security_report: Optional[Dict[str, Any]] = Field(None, description="Security screening audit report")
    
    # Mandatory Approval Lifecycle
    status: DraftApprovalStatus = Field(default=DraftApprovalStatus.DRAFT, description="Current workflow stage")
    human_reviewer: Optional[str] = Field(None, description="Name or ID of adjuster who reviewed")
    adjuster_modifications_notes: Optional[str] = Field(None, description="Notes on human adjuster edits")
    security_check_passed: bool = Field(default=False, description="True if automated PII and security checks passed")
    
    # Timestamps & Escalation
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Draft creation timestamp")
    reviewed_at_utc: Optional[datetime] = Field(None, description="Timestamp submitted/passed human review")
    approved_at_utc: Optional[datetime] = Field(None, description="Timestamp approved by adjuster")
    
    next_recommended_action: str = Field(..., description="Recommended strategy for claims adjuster")
    requires_escalation: bool = Field(default=False, description="True if evidence is insufficient to rebut objection")
    escalation_reason: Optional[str] = Field(None, description="Reason human adjuster escalation is mandated")


class SimulationTurn(BaseModel):
    """Single turn in a simulated interactive negotiation."""
    turn_index: int = Field(..., description="1-indexed round number (1, 2, 3)")
    inbound_carrier_message: InboundCarrierMessage
    outbound_draft: OutboundDraft
    status_at_turn_end: DraftApprovalStatus
    notes: str = Field(default="", description="Turn commentary or adjuster rationale")


class ThreeTurnNegotiationResult(BaseModel):
    """Complete summary of a 3-turn deterministic negotiation simulation."""
    simulation_id: str
    case_id: str
    starting_demand_usd: float
    final_settlement_usd: Optional[float]
    settlement_achieved: bool
    turns: List[SimulationTurn]
    completed_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
