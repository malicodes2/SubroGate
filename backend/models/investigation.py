from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .telemetry import TelemetryBreach, IncidentTelemetry, TelemetryThresholdConfig
from .documents import ExtractedEIRData, DocumentValidationReport, EIRExtractionResult


class CustodyRole(str, Enum):
    """Standard cargo transit custody roles."""
    SHIPPER = "SHIPPER"
    DRAYAGE_ORIGIN = "DRAYAGE_ORIGIN"
    ORIGIN_TERMINAL = "ORIGIN_TERMINAL"
    OCEAN_CARRIER = "OCEAN_CARRIER"
    RAIL_CARRIER = "RAIL_CARRIER"
    DESTINATION_TERMINAL = "DESTINATION_TERMINAL"
    DRAYAGE_DESTINATION = "DRAYAGE_DESTINATION"
    CONSIGNEE = "CONSIGNEE"
    UNKNOWN = "UNKNOWN"


class TimelineEventType(str, Enum):
    """Event classifications on reconstructed timeline."""
    CUSTODY_HANDOVER = "CUSTODY_HANDOVER"
    TELEMETRY_BREACH_START = "TELEMETRY_BREACH_START"
    TELEMETRY_BREACH_PEAK = "TELEMETRY_BREACH_PEAK"
    TELEMETRY_BREACH_END = "TELEMETRY_BREACH_END"
    DOCUMENT_EXCEPTION = "DOCUMENT_EXCEPTION"
    SENSOR_ANOMALY = "SENSOR_ANOMALY"


class CustodyWindow(BaseModel):
    """Continuous temporal window during which a specific entity held Care, Custody, and Control (CCC)."""
    window_id: str = Field(..., description="Unique window identifier (e.g. WIN-1)")
    holder_name: str = Field(..., description="Name of party holding custody")
    role: CustodyRole = Field(default=CustodyRole.UNKNOWN, description="Custody role")
    start_time_utc: datetime = Field(..., description="Start timestamp of custody in UTC")
    end_time_utc: Optional[datetime] = Field(None, description="End timestamp of custody in UTC (None if current custody)")
    start_location: Optional[str] = Field(None, description="Origin / handover location")
    end_location: Optional[str] = Field(None, description="Destination / release location")
    eir_handover_status: Optional[str] = Field(None, description="Incoming EIR condition status")
    eir_document_ref: Optional[str] = Field(None, description="Reference ID or filename of EIR document")
    is_active_window: bool = Field(default=False, description="True if custody window was active during transit")


class FusedTimelineEvent(BaseModel):
    """Unified chronological event combining telemetry time series and discrete document handovers."""
    event_id: str = Field(..., description="Unique event identifier (e.g. EVT-001)")
    timestamp_utc: datetime = Field(..., description="Normalized timestamp in UTC")
    event_type: TimelineEventType = Field(..., description="Classification of event")
    title: str = Field(..., description="Short descriptive title")
    description: str = Field(..., description="Detailed description of event facts")
    custody_holder: Optional[str] = Field(None, description="Entity having physical custody at this instant")
    custody_role: CustodyRole = Field(default=CustodyRole.UNKNOWN, description="Role of custody holder")
    severity: str = Field(default="INFO", description="INFO, WARNING, or CRITICAL")
    evidence_source: str = Field(..., description="Source of event (e.g. 'EIR Document', 'Sensor Logger')")
    is_breach_event: bool = Field(default=False, description="True if represents a threshold violation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context or raw values")


class DeterministicCustodyOverlap(BaseModel):
    """Algorithmic calculation determining which custody window overlaps the earliest recorded breach."""
    has_breach: bool = Field(default=False, description="True if any telemetry breach was recorded")
    culpable_party: Optional[str] = Field(None, description="Party having physical custody at earliest breach")
    culpable_role: CustodyRole = Field(default=CustodyRole.UNKNOWN, description="Role of culpable party")
    earliest_breach_timestamp_utc: Optional[datetime] = Field(None, description="First timestamp of breach in UTC")
    custody_window_id: Optional[str] = Field(None, description="ID of overlapping custody window")
    custody_window_start_utc: Optional[datetime] = Field(None, description="Custody start time in UTC")
    custody_window_end_utc: Optional[datetime] = Field(None, description="Custody end time in UTC")
    overlap_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Algorithmic confidence in temporal overlap")
    basis_reasoning: str = Field(..., description="Deterministic explanation of temporal overlap calculation")


class LegalFrameworkReference(BaseModel):
    """Explicitly sourced statutory regime and legal reference."""
    statutory_regime: str = Field(..., description="Governing legal framework (e.g. 'Carmack Amendment', 'COGSA', 'CMR')")
    citation: str = Field(..., description="Legal citation (e.g. '49 U.S.C. § 14706', '46 U.S.C. § 30701')")
    rule_summary: str = Field(..., description="Core legal rule / prima facie burden of proof standard")
    burden_of_proof_standard: str = Field(..., description="Standard for carrier liability and rebuttable presumption")
    source_document: str = Field(default="Federal Statutory Transport Law", description="Source reference")


class EvidenceCitation(BaseModel):
    """Verifiable citation linking an assertion to document text or sensor readings."""
    citation_id: str = Field(..., description="Unique citation key (e.g. CIT-01)")
    source_type: str = Field(..., description="'EIR_DOCUMENT', 'TELEMETRY_LOG', 'CASE_METADATA', or 'STATUTORY_SOURCE'")
    source_reference: str = Field(..., description="Document filename, row number, or statute name")
    verbatim_quote_or_datapoint: str = Field(..., description="Exact quoted text or sensor reading value")
    timestamp_utc: Optional[datetime] = Field(None, description="Associated timestamp in UTC if applicable")
    relevance_explanation: str = Field(..., description="Why this evidence supports or conflicts with the assessment")


class CaseDisputeMetadata(BaseModel):
    """Dispute context and known party information."""
    shipment_id: str = Field(default="SHIP-001", description="Unique shipment / dispute reference ID")
    shipper_name: str = Field(default="Origin Shipper Inc.", description="Shipper / origin consignor")
    carrier_name: Optional[str] = Field(None, description="Primary motor or ocean carrier involved in dispute")
    consignee_name: Optional[str] = Field(None, description="Destination receiving party")
    origin_facility: Optional[str] = Field(None, description="Origin port or warehouse")
    destination_facility: Optional[str] = Field(None, description="Destination port or warehouse")
    commodity: Optional[str] = Field(None, description="Description of cargo (e.g. Frozen Pharmaceuticals)")
    declared_value_usd: Optional[float] = Field(None, description="Declared cargo commercial value")
    claimed_loss_usd: Optional[float] = Field(None, description="Claimed damage amount in USD")
    governing_regime: Optional[str] = Field(default="Carmack Amendment", description="Governing legal framework")


class EvidenceBackedAssessment(BaseModel):
    """
    Forensic Evidence-Backed Responsibility Assessment.
    Explicitly marked as non-binding forensic deductions with supporting evidence citations.
    """
    shipment_id: str = Field(..., description="Shipment or claim reference identifier")
    assessment_timestamp_utc: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Assessment generation timestamp")
    
    # Responsibility Findings
    potentially_responsible_party: Optional[str] = Field(None, description="Entity identified as holding physical custody at breach")
    potentially_responsible_role: CustodyRole = Field(default=CustodyRole.UNKNOWN, description="Role of responsible entity")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Overall confidence based on evidence quality")
    
    # Deterministic Overlap Anchor
    deterministic_overlap: DeterministicCustodyOverlap = Field(..., description="Algorithmic custody overlap at earliest recorded breach")
    
    # Evidence Provenance
    supporting_evidence: List[EvidenceCitation] = Field(default_factory=list, description="Citations supporting the responsibility finding")
    conflicting_evidence: List[EvidenceCitation] = Field(default_factory=list, description="Citations presenting conflicting or contradictory facts")
    
    # Statutory & Contractual References
    applicable_framework: LegalFrameworkReference = Field(..., description="Explicitly sourced statutory framework")
    contractual_citations: List[str] = Field(default_factory=list, description="Applicable bill of lading or interchange terms")
    
    # Uncertainties & Action
    uncertainties_and_gaps: List[str] = Field(default_factory=list, description="Identified data gaps, missing intervals, or ambiguities")
    recommended_recovery_action: str = Field(..., description="Forensic recommendation for subrogation adjuster")
    human_review_required: bool = Field(default=True, description="True if claims adjuster review is required before action")
    
    # Mandatory Legal Boundary Disclaimer
    disclaimer: str = Field(
        default=(
            "LEGAL DISCLAIMER: This is an evidence-backed forensic responsibility assessment produced "
            "for cargo claims subrogation investigation. It does NOT constitute a binding legal ruling, "
            "judicial determination, or guarantee of legal liability. Final subrogation actions require "
            "review and authorization by a licensed claims professional."
        ),
        description="Mandatory legal disclaimer"
    )


class DisputeInvestigationRequest(BaseModel):
    """Request payload for the complete vertical slice."""
    case_metadata: CaseDisputeMetadata = Field(default_factory=CaseDisputeMetadata)
    telemetry_csv: str = Field(..., description="Raw CSV string of sensor telemetry readings")
    default_timezone: Optional[str] = Field(default=None, description="Default timezone for ambiguous timestamps")
    thresholds: Optional[TelemetryThresholdConfig] = Field(default=None, description="Sensor threshold configuration")
    eir_document_base64: Optional[str] = Field(default=None, description="Base64 encoded EIR PDF or image")
    eir_filename: Optional[str] = Field(default="gate_receipt.pdf", description="EIR filename")
    eir_mime_type: Optional[str] = Field(default="application/pdf", description="EIR MIME type")
    pre_extracted_eir: Optional[ExtractedEIRData] = Field(default=None, description="Pre-extracted EIR data if already parsed")


from .case import CaseModel


class DisputeInvestigationResponse(BaseModel):
    """End-to-end output of the SubroGate Vertical Slice."""
    shipment_id: str
    extracted_eir: Optional[EIRExtractionResult] = None
    normalized_telemetry: IncidentTelemetry
    reconstructed_timeline: List[FusedTimelineEvent]
    custody_windows: List[CustodyWindow]
    deterministic_overlap: DeterministicCustodyOverlap
    evidence_backed_assessment: EvidenceBackedAssessment
    execution_time_ms: float = 0.0
    case: Optional[CaseModel] = None
