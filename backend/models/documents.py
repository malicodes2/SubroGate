from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ExtractionStatus(str, Enum):
    """Application-level validation status for document extraction."""
    PASS = "PASS"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    FAILED = "FAILED"


class GateEventType(str, Enum):
    """Standardized cargo gate interchange event classifications."""
    INGATE = "INGATE"
    OUTGATE = "OUTGATE"
    INTERCHANGE = "INTERCHANGE"
    VESSEL_LOAD = "VESSEL_LOAD"
    VESSEL_DISCHARGE = "VESSEL_DISCHARGE"
    RAIL_RAMP_IN = "RAIL_RAMP_IN"
    RAIL_RAMP_OUT = "RAIL_RAMP_OUT"
    UNKNOWN = "UNKNOWN"


class HandoverCondition(str, Enum):
    """Physical condition of equipment and cargo at interchange."""
    CLEAN = "CLEAN"
    DAMAGE_NOTED = "DAMAGE_NOTED"
    SEAL_BROKEN_OR_MISSING = "SEAL_BROKEN_OR_MISSING"
    TEMPERATURE_EXCEPTION = "TEMPERATURE_EXCEPTION"
    REJECTED = "REJECTED"
    UNKNOWN = "UNKNOWN"


class ValidationFlag(str, Enum):
    """Audit flags indicating specific anomalies or verification needs."""
    AMBIGUOUS_TIMEZONE = "AMBIGUOUS_TIMEZONE"
    TIMESTAMP_PARSE_FAILURE = "TIMESTAMP_PARSE_FAILURE"
    UNSUPPORTED_TIMESTAMP_EVIDENCE = "UNSUPPORTED_TIMESTAMP_EVIDENCE"
    CONTAINER_ID_CHECKSUM_WARNING = "CONTAINER_ID_CHECKSUM_WARNING"
    CONTAINER_ID_MISMATCH = "CONTAINER_ID_MISMATCH"
    INVALID_CONTAINER_FORMAT = "INVALID_CONTAINER_FORMAT"
    CARRIER_MISMATCH = "CARRIER_MISMATCH"
    CARRIER_UNKNOWN = "CARRIER_UNKNOWN"
    MISSING_CRITICAL_FIELD = "MISSING_CRITICAL_FIELD"
    MISSING_EVIDENCE_QUOTE = "MISSING_EVIDENCE_QUOTE"
    CONFLICTING_TIMESTAMPS = "CONFLICTING_TIMESTAMPS"
    CONFLICTING_CONDITION_EVIDENCE = "CONFLICTING_CONDITION_EVIDENCE"
    HANDWRITING_AMBIGUITY = "HANDWRITING_AMBIGUITY"
    ROTATED_STAMP_EXCEPTION = "ROTATED_STAMP_EXCEPTION"
    UNREADABLE_SECTIONS = "UNREADABLE_SECTIONS"
    LOW_MODEL_CONFIDENCE = "LOW_MODEL_CONFIDENCE"


class FieldEvidence(BaseModel):
    """Traceable evidence linking an extracted value back to the source document."""
    field_name: str = Field(..., description="Name of the attribute (e.g. 'container_id')")
    extracted_value: Optional[Any] = Field(None, description="The extracted structured value")
    raw_text: Optional[str] = Field(None, description="Raw text string as seen in document")
    verbatim_quote: Optional[str] = Field(None, description="Surrounding text snippet/quote supporting this extraction")
    page_number: int = Field(default=1, description="1-indexed source page or image number")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Model self-reported extraction confidence (0.0 to 1.0)")
    is_verified: bool = Field(default=False, description="True if verified by application-level validation logic")
    notes: Optional[str] = Field(None, description="Notes on font, handwriting, rotation, or stamp characteristics")


class SealInformation(BaseModel):
    """Seal verification details extracted from EIR."""
    seal_number: Optional[str] = Field(None, description="Extracted seal number")
    seal_intact: bool = Field(default=True, description="True if seal is recorded intact")
    seal_tampered_or_missing: bool = Field(default=False, description="True if seal breach was noted")
    evidence: Optional[FieldEvidence] = None


class ReeferInformation(BaseModel):
    """Refrigeration parameters recorded at gate handover."""
    setpoint_temp_c: Optional[float] = Field(None, description="Target setpoint temperature in Celsius")
    actual_temp_c: Optional[float] = Field(None, description="Actual recorded cargo temperature in Celsius")
    genset_running: Optional[bool] = Field(None, description="Whether generator set was powered on")
    vent_open_pct: Optional[float] = Field(None, description="Ventilation setting percentage if noted")
    evidence: Optional[FieldEvidence] = None


class ExtractedEIRData(BaseModel):
    """Raw structured data extracted from the document before application validation."""
    carrier_name: Optional[str] = Field(None, description="Name of carrier / motor carrier / shipping line")
    releasing_entity: Optional[str] = Field(None, description="Facility or party transferring custody")
    receiving_entity: Optional[str] = Field(None, description="Party receiving care, custody, and control")
    container_id: Optional[str] = Field(None, description="4-letter prefix + 7-digit container ID (e.g. MSKU9082341)")
    chassis_id: Optional[str] = Field(None, description="Chassis or trailer unit identifier")
    tractor_license_plate: Optional[str] = Field(None, description="Tractor / truck license plate or unit number")
    driver_name: Optional[str] = Field(None, description="Driver name if printed or signed")
    
    gate_event_type: GateEventType = Field(default=GateEventType.UNKNOWN, description="Gate transaction type")
    raw_timestamp_str: Optional[str] = Field(None, description="Original unparsed timestamp string from document")
    extracted_timezone_str: Optional[str] = Field(None, description="Timezone token or offset if printed (e.g. 'EDT', '-04:00')")
    facility_location: Optional[str] = Field(None, description="Terminal, port, depot, or warehouse name and address")
    
    condition_summary: HandoverCondition = Field(default=HandoverCondition.UNKNOWN, description="Overall equipment condition")
    damage_remarks: Optional[str] = Field(None, description="Specific damage remarks or inspection notes")
    handwritten_notes: List[str] = Field(default_factory=list, description="Transcribed handwritten annotations")
    stamps_detected: List[Dict[str, Any]] = Field(default_factory=list, description="Detected physical rubber stamps or digital endorsements")
    
    seal_info: Optional[SealInformation] = None
    reefer_info: Optional[ReeferInformation] = None
    
    unreadable_sections: List[str] = Field(default_factory=list, description="Sections noted as blurry, cut off, or illegible")
    field_evidence_map: Dict[str, FieldEvidence] = Field(default_factory=dict, description="Map of field names to evidence provenance")


class DocumentValidationReport(BaseModel):
    """Application-level deterministic audit report for extracted document."""
    status: ExtractionStatus = Field(..., description="Final validation status: PASS, REVIEW_REQUIRED, or FAILED")
    requires_human_verification: bool = Field(..., description="True if claims adjuster review is mandated")
    validation_flags: List[ValidationFlag] = Field(default_factory=list, description="Categorical audit flags")
    errors: List[str] = Field(default_factory=list, description="Blocking validation failures")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking audit warnings")
    
    # Audit Breakdown
    is_timestamp_parseable: bool = Field(default=False, description="True if timestamp parsed to valid UTC datetime")
    normalized_timestamp_utc: Optional[datetime] = Field(None, description="Normalized UTC timestamp if parseable")
    is_timezone_explicit: bool = Field(default=False, description="True if explicit timezone was present in document")
    
    is_container_id_valid_iso: bool = Field(default=False, description="True if container ID satisfies ISO 6346 format and check digit")
    container_id_checksum_matches: bool = Field(default=False, description="True if ISO 6346 modulo 11 check digit matches")
    matches_expected_container_id: Optional[bool] = Field(None, description="True if matches case context expected container ID")
    
    matches_expected_carrier: Optional[bool] = Field(None, description="True if carrier matches known case parties")
    timestamp_has_supporting_evidence: bool = Field(default=False, description="True if timestamp appears in document text evidence")


class DocumentMetadata(BaseModel):
    """File metadata and cryptographic fingerprint for audit traceability."""
    document_id: str = Field(..., description="Unique document ID (e.g. DOC-9842)")
    filename: str = Field(..., description="Original filename uploaded")
    file_size_bytes: int = Field(..., description="File size in bytes")
    mime_type: str = Field(..., description="MIME type (e.g. application/pdf, image/jpeg)")
    sha256_hash: str = Field(..., description="Cryptographic SHA-256 hash of raw file bytes")
    total_pages: int = Field(default=1, description="Number of pages in document")
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of extraction")


class EIRExtractionResult(BaseModel):
    """Full end-to-end response for Document Intelligence extraction and validation."""
    document_metadata: DocumentMetadata
    extraction_status: ExtractionStatus = Field(..., description="Overall status: PASS, REVIEW_REQUIRED, or FAILED")
    extracted_data: Optional[ExtractedEIRData] = None
    validation_report: DocumentValidationReport
    model_name_used: str = Field(..., description="Gemini model utilized (from centralized configuration)")
    execution_time_ms: float = Field(default=0.0, description="End-to-end extraction and validation latency in ms")
    raw_model_response: Optional[Dict[str, Any]] = Field(None, description="Structured payload as returned by model")
