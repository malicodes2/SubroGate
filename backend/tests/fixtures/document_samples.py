import io
from typing import Dict, Any, Tuple
from backend.models.documents import (
    ExtractedEIRData,
    FieldEvidence,
    SealInformation,
    ReeferInformation,
    GateEventType,
    HandoverCondition
)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def create_synthetic_pdf(text_lines: list, title: str = "Equipment Interchange Receipt") -> bytes:
    """Generates a real PDF binary in memory for test fixtures."""
    buffer = io.BytesIO()
    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(buffer, pagesize=letter)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, 750, title)
        c.setFont("Helvetica", 10)
        y = 720
        for line in text_lines:
            c.drawString(50, y, line)
            y -= 20
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    else:
        # Fallback raw PDF header for testing when reportlab is not installed
        dummy_content = f"%PDF-1.4\n1 0 obj\n<< /Title ({title}) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
        return dummy_content.encode("utf-8")


# ==============================================================================
# 1. CLEAN SAMPLE DOCUMENT
# ==============================================================================
CLEAN_DOCUMENT_TEXT = [
    "TERMINAL: APM Terminals Pier 400 Los Angeles",
    "CARRIER: Apex Drayage LLC (DOT# 2948102)",
    "TRANSACTION: IN-GATE LOADED INTERCHANGE",
    "CONTAINER NO: MSKU9082345 (40ft High Cube)",
    "CHASSIS NO: CHAZ-98412",
    "SEAL NO: ML-US994821 (INTACT AND VERIFIED)",
    "HANDOVER TIMESTAMP: 2026-06-15 14:30:00 EDT",
    "REEFER SETPOINT: -20.0 C | ACTUAL TEMP: -19.8 C | GENSET: RUNNING",
    "CONDITION: CLEAN - NO VISIBLE EXTERNAL DAMAGE",
    "CLERK SIGNATURE: J. Smith #4481"
]

CLEAN_EXTRACTED_DATA = ExtractedEIRData(
    carrier_name="Apex Drayage LLC",
    releasing_entity="Apex Drayage LLC",
    receiving_entity="APM Terminals Pier 400",
    container_id="MSKU9082345",
    chassis_id="CHAZ-98412",
    tractor_license_plate=None,
    driver_name="J. Smith",
    gate_event_type=GateEventType.INGATE,
    raw_timestamp_str="2026-06-15 14:30:00 EDT",
    extracted_timezone_str="EDT",
    facility_location="APM Terminals Pier 400 Los Angeles",
    condition_summary=HandoverCondition.CLEAN,
    damage_remarks=None,
    handwritten_notes=[],
    stamps_detected=[{"text": "IN-GATE VERIFIED", "rotation_deg": 0, "status": "APPROVED"}],
    seal_info=SealInformation(
        seal_number="ML-US994821",
        seal_intact=True,
        seal_tampered_or_missing=False,
        evidence=FieldEvidence(
            field_name="seal_number",
            extracted_value="ML-US994821",
            raw_text="ML-US994821",
            verbatim_quote="SEAL NO: ML-US994821 (INTACT AND VERIFIED)",
            page_number=1,
            confidence=0.99
        )
    ),
    reefer_info=ReeferInformation(
        setpoint_temp_c=-20.0,
        actual_temp_c=-19.8,
        genset_running=True,
        evidence=FieldEvidence(
            field_name="reefer_info",
            extracted_value=-19.8,
            verbatim_quote="REEFER SETPOINT: -20.0 C | ACTUAL TEMP: -19.8 C",
            page_number=1,
            confidence=0.98
        )
    ),
    unreadable_sections=[],
    field_evidence_map={
        "container_id": FieldEvidence(
            field_name="container_id",
            extracted_value="MSKU9082345",
            raw_text="MSKU9082345",
            verbatim_quote="CONTAINER NO: MSKU9082345 (40ft High Cube)",
            page_number=1,
            confidence=0.99
        ),
        "raw_timestamp_str": FieldEvidence(
            field_name="raw_timestamp_str",
            extracted_value="2026-06-15 14:30:00 EDT",
            raw_text="2026-06-15 14:30:00 EDT",
            verbatim_quote="HANDOVER TIMESTAMP: 2026-06-15 14:30:00 EDT",
            page_number=1,
            confidence=0.99
        ),
        "carrier_name": FieldEvidence(
            field_name="carrier_name",
            extracted_value="Apex Drayage LLC",
            raw_text="Apex Drayage LLC",
            verbatim_quote="CARRIER: Apex Drayage LLC (DOT# 2948102)",
            page_number=1,
            confidence=0.97
        )
    }
)


# ==============================================================================
# 2. ROTATED DOCUMENT SAMPLE
# ==============================================================================
ROTATED_DOCUMENT_TEXT = [
    "GLOBAL CONTAINER TERMINAL BAYONNE",
    "OUT-GATE INTERCHANGE RECEIPT",
    "UNIT: CMAU7182935",
    "CARRIER: Swift Intermodal",
    "TIMESTAMP: 2026-06-18 09:15:00-04:00",
    "[STAMP ROTATED 90 DEG: EXCEPTION NOTED - REAR DOOR HINGE LOOSE]",
    "SEAL: SW-884192",
    "CONDITION: DAMAGE_NOTED"
]

ROTATED_EXTRACTED_DATA = ExtractedEIRData(
    carrier_name="Swift Intermodal",
    container_id="CMAU7182935",
    gate_event_type=GateEventType.OUTGATE,
    raw_timestamp_str="2026-06-18 09:15:00-04:00",
    extracted_timezone_str="-04:00",
    facility_location="Global Container Terminal Bayonne",
    condition_summary=HandoverCondition.DAMAGE_NOTED,
    damage_remarks="Rear door hinge loose noted on rotated gate stamp",
    handwritten_notes=[],
    stamps_detected=[{
        "text": "EXCEPTION NOTED - REAR DOOR HINGE LOOSE",
        "rotation_deg": 90,
        "status": "EXCEPTION"
    }],
    seal_info=SealInformation(seal_number="SW-884192", seal_intact=True),
    unreadable_sections=[],
    field_evidence_map={
        "container_id": FieldEvidence(
            field_name="container_id",
            extracted_value="CMAU7182935",
            raw_text="CMAU7182935",
            verbatim_quote="UNIT: CMAU7182935",
            page_number=1,
            confidence=0.95
        ),
        "raw_timestamp_str": FieldEvidence(
            field_name="raw_timestamp_str",
            extracted_value="2026-06-18 09:15:00-04:00",
            raw_text="2026-06-18 09:15:00-04:00",
            verbatim_quote="TIMESTAMP: 2026-06-18 09:15:00-04:00",
            page_number=1,
            confidence=0.96
        )
    }
)


# ==============================================================================
# 3. POOR-QUALITY / DEGRADED SCAN
# ==============================================================================
POOR_QUALITY_EXTRACTED_DATA = ExtractedEIRData(
    carrier_name="Maersk Logistics",
    container_id="MSKU1234567",  # Check digit intentionally incorrect (calculated is 4, document says 7)
    gate_event_type=GateEventType.INGATE,
    raw_timestamp_str="2026-06-20 11:00:00 UTC",
    extracted_timezone_str="UTC",
    facility_location="Port of Savannah Garden City Terminal",
    condition_summary=HandoverCondition.CLEAN,
    unreadable_sections=["Bottom left driver signature and barcode smeared", "Weight ticket blurred"],
    field_evidence_map={
        "container_id": FieldEvidence(
            field_name="container_id",
            extracted_value="MSKU1234567",
            raw_text="MSKU 123456-7?",
            verbatim_quote="CTR: MSKU 123456-7",
            page_number=1,
            confidence=0.60  # Low confidence
        ),
        "raw_timestamp_str": FieldEvidence(
            field_name="raw_timestamp_str",
            extracted_value="2026-06-20 11:00:00 UTC",
            raw_text="2026-06-20 11:00:00 UTC",
            verbatim_quote="TIME: 2026-06-20 11:00:00 UTC",
            page_number=1,
            confidence=0.85
        )
    }
)


# ==============================================================================
# 4. AMBIGUOUS DOCUMENT (Multiple timestamps, Missing TZ, Handwritten note)
# ==============================================================================
AMBIGUOUS_DOCUMENT_TEXT = [
    "CSX INTERMODAL TERMINAL FAIRMONT",
    "RAMP INGATE RECEIPT",
    "CONTAINER: TCLU8910234",
    "SCALE TIME: 2026-06-22 14:10",
    "GATE IN TIME: 2026-06-22 14:30",  # Missing timezone indicator!
    "RECEIPT PRINTED: 2026-06-22 14:45",
    "HANDWRITING: Driver noted small roof scrape on arrival",
    "CONDITION: CLEAN"  # Conflicting with handwriting!
]

AMBIGUOUS_EXTRACTED_DATA = ExtractedEIRData(
    carrier_name="CSX Transportation",
    container_id="TCLU8910234",
    gate_event_type=GateEventType.RAIL_RAMP_IN,
    raw_timestamp_str="2026-06-22 14:30",  # Ambiguous timezone
    extracted_timezone_str=None,  # No timezone token on receipt
    facility_location="CSX Fairmont Intermodal",
    condition_summary=HandoverCondition.CLEAN,
    handwritten_notes=["Driver noted small roof scrape on arrival"],
    unreadable_sections=[],
    field_evidence_map={
        "container_id": FieldEvidence(
            field_name="container_id",
            extracted_value="TCLU8910234",
            raw_text="TCLU8910234",
            verbatim_quote="CONTAINER: TCLU8910234",
            page_number=1,
            confidence=0.92
        ),
        "raw_timestamp_str": FieldEvidence(
            field_name="raw_timestamp_str",
            extracted_value="2026-06-22 14:30",
            raw_text="2026-06-22 14:30",
            verbatim_quote="GATE IN TIME: 2026-06-22 14:30",
            page_number=1,
            confidence=0.91
        )
    }
)


# ==============================================================================
# 5. UNREADABLE / CORRUPT DOCUMENT
# ==============================================================================
UNREADABLE_EXTRACTED_DATA = ExtractedEIRData(
    carrier_name=None,
    container_id=None,
    gate_event_type=GateEventType.UNKNOWN,
    raw_timestamp_str=None,
    extracted_timezone_str=None,
    facility_location=None,
    condition_summary=HandoverCondition.UNKNOWN,
    unreadable_sections=["Entire document is completely blacked out / illegible"],
    field_evidence_map={}
)


def get_all_document_fixtures() -> Dict[str, Tuple[bytes, ExtractedEIRData]]:
    """Returns a dict of all 5 synthetic document fixtures with raw PDF bytes and mock data."""
    return {
        "clean": (create_synthetic_pdf(CLEAN_DOCUMENT_TEXT, "APM Terminals EIR Clean"), CLEAN_EXTRACTED_DATA),
        "rotated": (create_synthetic_pdf(ROTATED_DOCUMENT_TEXT, "GCT Bayonne Rotated EIR"), ROTATED_EXTRACTED_DATA),
        "poor_quality": (create_synthetic_pdf(["[LOW CONTRAST / FAINT SCAN]"], "Degraded EIR"), POOR_QUALITY_EXTRACTED_DATA),
        "ambiguous": (create_synthetic_pdf(AMBIGUOUS_DOCUMENT_TEXT, "CSX Rail Ambiguous EIR"), AMBIGUOUS_EXTRACTED_DATA),
        "unreadable": (b"%PDF-1.4 CORRUPTED UNREADABLE BYTES \x00\xff\xfe", UNREADABLE_EXTRACTED_DATA),
    }
