from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class CaseStatus(str, Enum):
    """Explicit lifecycle statuses for a cargo dispute subrogation case."""
    NEW = "NEW"
    INGESTING = "INGESTING"
    ANALYZING = "ANALYZING"
    ASSESSMENT_READY = "ASSESSMENT_READY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    APPROVED = "APPROVED"
    AWAITING_RESPONSE = "AWAITING_RESPONSE"
    NEGOTIATION = "NEGOTIATION"
    RESOLVED = "RESOLVED"
    FAILED = "FAILED"


class ShipmentInfo(BaseModel):
    """Core shipment and cargo identification."""
    container_id: Optional[str] = Field(None, description="Container / trailer identifier (e.g. MSKU9082345)")
    commodity: Optional[str] = Field(None, description="Cargo description (e.g. Frozen Pharmaceuticals)")
    declared_value_usd: Optional[float] = Field(None, description="Commercial cargo value in USD")
    claimed_loss_usd: Optional[float] = Field(None, description="Claimed damage amount in USD")
    origin_facility: Optional[str] = Field(None, description="Origin port or warehouse facility")
    destination_facility: Optional[str] = Field(None, description="Destination terminal or consignee facility")
    shipper_name: Optional[str] = Field(None, description="Origin shipper / consignor")
    carrier_name: Optional[str] = Field(None, description="Responsible motor or ocean carrier")
    consignee_name: Optional[str] = Field(None, description="Destination receiving party")
    bill_of_lading_number: Optional[str] = Field(None, description="Master or house bill of lading number")


class SourceDocumentRef(BaseModel):
    """Traceable reference to ingested physical document (EIR, Bill of Lading, etc.)."""
    document_id: str = Field(..., description="Unique document ID (e.g. DOC-9842)")
    filename: str = Field(..., description="Uploaded document filename")
    mime_type: str = Field(..., description="MIME type (e.g. application/pdf, image/jpeg)")
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 hash of document")
    file_size_bytes: int = Field(default=0, description="File size in bytes")
    uploaded_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Upload timestamp")
    document_type: str = Field(default="EIR", description="EIR, BOL, SURVEY_REPORT, or INVOICE")


class TelemetryRef(BaseModel):
    """Summary reference to ingested IoT sensor telemetry time-series."""
    device_id: Optional[str] = Field(None, description="Sensor logger device serial ID")
    total_readings_count: int = Field(default=0, description="Count of parsed readings")
    breaches_detected_count: int = Field(default=0, description="Count of threshold breach intervals")
    earliest_reading_utc: Optional[datetime] = Field(None, description="First sensor reading timestamp")
    latest_reading_utc: Optional[datetime] = Field(None, description="Last sensor reading timestamp")
    has_critical_shock: bool = Field(default=False, description="True if high-G shock violation detected")
    has_temp_excursion: bool = Field(default=False, description="True if reefer temperature excursion detected")
    file_name: Optional[str] = Field(None, description="Uploaded file name")
    sample_count: int = Field(default=0, description="Number of samples")
    ingestion_mode: Optional[str] = Field(None, description="How the telemetry was ingested")
    peak_shock_g: Optional[float] = Field(None, description="Max shock recorded")
    peak_temp_c: Optional[float] = Field(None, description="Max temp excursion")
    breach_custodian: Optional[str] = Field(None, description="Custodian at time of breach")
    points: List[Dict[str, Any]] = Field(default_factory=list, description="Downsampled points for rendering")


class HumanApprovalEvent(BaseModel):
    """Audit record of human claims adjuster approval gate."""
    approval_id: str = Field(..., description="Unique approval identifier")
    adjuster_name: str = Field(..., description="Name or ID of licensed claims adjuster")
    approved_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of approval")
    allocated_liability_pct: float = Field(default=100.0, ge=0.0, le=100.0, description="Approved liability allocation %")
    notes: Optional[str] = Field(None, description="Adjuster assessment notes or rationale")
    audit_badge_token: str = Field(..., description="Cryptographic or hash token proving human sign-off")


class SettlementState(BaseModel):
    """Subrogation recovery negotiation posture and financial targets."""
    target_recovery_usd: float = Field(default=0.0, description="Target full recovery amount in USD")
    acceptable_settlement_floor_usd: float = Field(default=0.0, description="Minimum acceptable settlement floor in USD")
    recommended_posture: str = Field(default="FIRM_ASSERTIVE", description="Negotiation posture (e.g. FIRM_ASSERTIVE, COOPERATIVE)")
    current_carrier_offer_usd: Optional[float] = Field(None, description="Latest offer received from carrier")
    settlement_status: str = Field(default="PENDING_DEMAND", description="PENDING_DEMAND, OFFER_RECEIVED, COUNTER_OFFERED, SETTLED, DENIED")


class NegotiationMessage(BaseModel):
    """Record of communication during subrogation recovery negotiation."""
    message_id: str = Field(..., description="Unique message ID (e.g. MSG-001)")
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Message timestamp")
    sender_party: str = Field(..., description="Entity sending communication (e.g. 'SubroGate Adjuster', 'Carrier Claims Dept')")
    recipient_party: str = Field(..., description="Entity receiving communication")
    message_type: str = Field(default="FORMAL_DEMAND", description="FORMAL_DEMAND, REBUTTAL, COUNTER_OFFER, SETTLEMENT_AGREEMENT, DENIAL")
    message_text: str = Field(..., description="Body of communication / markdown notice")
    proposed_amount_usd: Optional[float] = Field(None, description="Proposed settlement amount if applicable")
    response_deadline_utc: Optional[datetime] = Field(None, description="Deadline for response")


class AuditEvent(BaseModel):
    """Immutable audit trail entry documenting actions on the case."""
    event_id: str = Field(..., description="Unique audit event ID (e.g. AUD-001)")
    event_type: str = Field(..., description="Event classification (e.g. 'CASE_CREATED', 'STATUS_CHANGED', 'ASSESSMENT_ATTACHED')")
    description: str = Field(..., description="Human-readable description of the action")
    actor: str = Field(default="SYSTEM", description="User, service, or agent that executed the action")
    timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of event")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Structured event metadata or payload snapshot")


class CaseModel(BaseModel):
    """
    SubroGate Persistent Case Model (Firestore Entity).
    Tracks the full lifecycle of a cargo transit dispute.
    """
    case_id: str = Field(..., description="Unique case identifier (e.g. CASE-2026-A8B9C0)")
    status: CaseStatus = Field(default=CaseStatus.NEW, description="Current lifecycle status")
    shipment_info: ShipmentInfo = Field(default_factory=ShipmentInfo, description="Shipment metadata and container details")
    
    # Ingested References
    source_document_refs: List[SourceDocumentRef] = Field(default_factory=list, description="References to ingested documents")
    telemetry_ref: Optional[TelemetryRef] = Field(None, description="Reference to ingested sensor telemetry")
    
    # Forensic Investigation Snapshots
    extracted_custody_events: Optional[Dict[str, Any]] = Field(None, description="Snapshot of extracted EIR data")
    normalized_timeline: List[Dict[str, Any]] = Field(default_factory=list, description="Reconstructed chronological timeline events")
    assessment: Optional[Dict[str, Any]] = Field(None, description="Snapshot of EvidenceBackedAssessment")
    
    # Human Review & Recovery State
    human_approvals: List[HumanApprovalEvent] = Field(default_factory=list, description="Human adjuster approvals")
    settlement_state: Optional[SettlementState] = Field(None, description="Settlement target and recovery state")
    negotiation_history: List[NegotiationMessage] = Field(default_factory=list, description="Communication & negotiation rounds")
    
    # System Metadata
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
    closed_at_utc: Optional[datetime] = Field(None, description="Timestamp when case was resolved or closed")
    model_identifier: str = Field(default="gemini-3.5-flash", description="Configured Gemini model ID used for assessment")
    application_version: str = Field(default="1.0.0", description="Application version")
    
    # Immutable Audit Log & Optimistic Concurrency Version
    audit_events: List[AuditEvent] = Field(default_factory=list, description="Append-only audit trail")
    version: int = Field(default=1, ge=1, description="Optimistic locking version counter (increments on each update)")
