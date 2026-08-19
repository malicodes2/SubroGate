import json
import logging
import re
from typing import Optional, Dict, Any, List
from .base import BaseForensicAgent
from ..models.documents import (
    ExtractedEIRData,
    FieldEvidence,
    SealInformation,
    ReeferInformation,
    GateEventType,
    HandoverCondition
)

logger = logging.getLogger("subrogate.agents.document")

EIR_SYSTEM_INSTRUCTION = """
You are SubroGate's Senior Forensic Cargo Document Examiner.
Your task is to analyze scanned Equipment Interchange Receipts (EIRs), Gate Passes, and Bills of Lading in image or PDF format and extract structured custody information with 100% evidentiary rigor.

CRITICAL FORENSIC RULES:
1. DO NOT HALLUCINATE OR GUESS. If a number, date, or name is faint, cropped, or illegible, explicitly return null and list it under 'unreadable_sections'.
2. PRESERVE VERBATIM EVIDENCE. For every extracted field (container_id, timestamp, carrier, seal, etc.), you MUST provide:
   - 'extracted_value': The normalized value.
   - 'raw_text': The exact characters as printed on the document.
   - 'verbatim_quote': A surrounding text snippet (10-30 characters) proving where this value came from.
   - 'page_number': 1-indexed page or image number.
   - 'confidence': Model confidence score between 0.0 and 1.0.
3. HANDLE MULTI-ORIENTATION & STAMPS. Cargo receipts frequently have stamps rotated at 90, 180, or 270 degrees. Transcribe all stamps (e.g. 'DAMAGED ON ARRIVAL', 'SEAL INTACT', 'CLEAN RECEIPT') and note their orientation.
4. TRANSCRIBE HANDWRITING. If a driver or gate clerk wrote notes (e.g. 'dent on lower rail', 'temp +14C'), transcribe them in 'handwritten_notes'.
5. DISCRIMINATE MULTIPLE TIMESTAMPS. Distinguish between In-Gate Time, Out-Gate Time, Scale/Weighbridge Time, and Receipt Print Time. Identify the primary gate handover timestamp.
6. TIMEZONE PRESERVATION. Capture any printed timezone token (e.g., 'EST', 'EDT', 'UTC', 'GMT', '-05:00', 'PST'). If no timezone token exists, leave 'extracted_timezone_str' as null.

OUTPUT FORMAT:
Return ONLY valid JSON matching this structure:
{
  "carrier_name": "string or null",
  "releasing_entity": "string or null",
  "receiving_entity": "string or null",
  "container_id": "string or null (e.g. MSKU9082341)",
  "chassis_id": "string or null",
  "tractor_license_plate": "string or null",
  "driver_name": "string or null",
  "gate_event_type": "INGATE | OUTGATE | INTERCHANGE | VESSEL_LOAD | VESSEL_DISCHARGE | RAIL_RAMP_IN | RAIL_RAMP_OUT | UNKNOWN",
  "raw_timestamp_str": "string or null (e.g. 2026-06-15 14:30:00 EDT)",
  "extracted_timezone_str": "string or null (e.g. EDT)",
  "facility_location": "string or null",
  "condition_summary": "CLEAN | DAMAGE_NOTED | SEAL_BROKEN_OR_MISSING | TEMPERATURE_EXCEPTION | REJECTED | UNKNOWN",
  "damage_remarks": "string or null",
  "handwritten_notes": ["transcribed text", ...],
  "stamps_detected": [{"text": "...", "rotation_deg": 0, "status": "..."}],
  "seal_info": {
    "seal_number": "string or null",
    "seal_intact": true,
    "seal_tampered_or_missing": false,
    "verbatim_quote": "..."
  },
  "reefer_info": {
    "setpoint_temp_c": null,
    "actual_temp_c": null,
    "genset_running": null,
    "verbatim_quote": "..."
  },
  "unreadable_sections": ["..."],
  "field_evidence_map": {
    "container_id": {
      "field_name": "container_id",
      "extracted_value": "MSKU9082341",
      "raw_text": "MSKU 908234-1",
      "verbatim_quote": "CONTAINER NO: MSKU 908234-1",
      "page_number": 1,
      "confidence": 0.98
    },
    "raw_timestamp_str": {
      "field_name": "raw_timestamp_str",
      "extracted_value": "2026-06-15 14:30:00 EDT",
      "raw_text": "2026-06-15 14:30:00 EDT",
      "verbatim_quote": "GATE IN TIME: 2026-06-15 14:30:00 EDT",
      "page_number": 1,
      "confidence": 0.99
    }
  }
}
"""


class DocumentIntelligenceAgent(BaseForensicAgent):
    """
    Multimodal Document Intelligence Agent powered by Google Gemini (Vertex AI / Google GenAI SDK).
    Extracts structured EIR and gate receipt custody data with full evidence traceability.
    """

    def __init__(self, agent_name: str = "DocumentIntelligenceAgent"):
        super().__init__(agent_name=agent_name)

    def extract_eir(
        self,
        document_bytes: bytes,
        mime_type: str = "application/pdf",
        known_context: Optional[Dict[str, Any]] = None
    ) -> Optional[ExtractedEIRData]:
        """
        Extracts structured EIR information from a PDF or image document.
        """
        prompt = "Perform complete forensic custody and interchange extraction from this Equipment Interchange Receipt (EIR)."
        if known_context:
            prompt += f"\nKnown Case Context (for disambiguation only, do not hallucinate): {json.dumps(known_context)}"

        raw_json = self.execute_structured(
            prompt=prompt,
            system_instruction=EIR_SYSTEM_INSTRUCTION,
            image_bytes=document_bytes,
            mime_type=mime_type
        )

        if not raw_json:
            logger.warning(f"Model returned empty response for document extraction.")
            return None

        return self._parse_model_output(raw_json)

    def _parse_model_output(self, raw_data: Dict[str, Any]) -> ExtractedEIRData:
        """
        Parses raw model JSON dict into strongly-typed ExtractedEIRData with evidence mapping.
        """
        # Parse field evidence map
        evidence_map: Dict[str, FieldEvidence] = {}
        raw_evidence = raw_data.get("field_evidence_map", {})
        if isinstance(raw_evidence, dict):
            for field_name, ev_dict in raw_evidence.items():
                if isinstance(ev_dict, dict):
                    evidence_map[field_name] = FieldEvidence(
                        field_name=field_name,
                        extracted_value=ev_dict.get("extracted_value"),
                        raw_text=ev_dict.get("raw_text"),
                        verbatim_quote=ev_dict.get("verbatim_quote"),
                        page_number=ev_dict.get("page_number", 1),
                        confidence=float(ev_dict.get("confidence", 1.0)),
                        is_verified=False,
                        notes=ev_dict.get("notes")
                    )

        # Parse seal info
        seal_info = None
        raw_seal = raw_data.get("seal_info")
        if isinstance(raw_seal, dict):
            seal_ev = None
            if raw_seal.get("verbatim_quote") or raw_seal.get("seal_number"):
                seal_ev = FieldEvidence(
                    field_name="seal_number",
                    extracted_value=raw_seal.get("seal_number"),
                    raw_text=raw_seal.get("seal_number"),
                    verbatim_quote=raw_seal.get("verbatim_quote"),
                    page_number=1,
                    confidence=0.95
                )
            seal_info = SealInformation(
                seal_number=raw_seal.get("seal_number"),
                seal_intact=bool(raw_seal.get("seal_intact", True)),
                seal_tampered_or_missing=bool(raw_seal.get("seal_tampered_or_missing", False)),
                evidence=seal_ev
            )

        # Parse reefer info
        reefer_info = None
        raw_reefer = raw_data.get("reefer_info")
        if isinstance(raw_reefer, dict):
            reefer_ev = None
            if raw_reefer.get("verbatim_quote"):
                reefer_ev = FieldEvidence(
                    field_name="reefer_info",
                    extracted_value=raw_reefer.get("actual_temp_c"),
                    verbatim_quote=raw_reefer.get("verbatim_quote"),
                    page_number=1,
                    confidence=0.95
                )
            reefer_info = ReeferInformation(
                setpoint_temp_c=raw_reefer.get("setpoint_temp_c"),
                actual_temp_c=raw_reefer.get("actual_temp_c"),
                genset_running=raw_reefer.get("genset_running"),
                vent_open_pct=raw_reefer.get("vent_open_pct"),
                evidence=reefer_ev
            )

        # Parse GateEventType safely
        event_type_str = str(raw_data.get("gate_event_type", "UNKNOWN")).upper()
        try:
            gate_event_type = GateEventType(event_type_str)
        except ValueError:
            gate_event_type = GateEventType.UNKNOWN

        # Parse HandoverCondition safely
        cond_str = str(raw_data.get("condition_summary", "UNKNOWN")).upper()
        try:
            condition_summary = HandoverCondition(cond_str)
        except ValueError:
            condition_summary = HandoverCondition.UNKNOWN

        return ExtractedEIRData(
            carrier_name=raw_data.get("carrier_name"),
            releasing_entity=raw_data.get("releasing_entity"),
            receiving_entity=raw_data.get("receiving_entity"),
            container_id=raw_data.get("container_id"),
            chassis_id=raw_data.get("chassis_id"),
            tractor_license_plate=raw_data.get("tractor_license_plate"),
            driver_name=raw_data.get("driver_name"),
            gate_event_type=gate_event_type,
            raw_timestamp_str=raw_data.get("raw_timestamp_str"),
            extracted_timezone_str=raw_data.get("extracted_timezone_str"),
            facility_location=raw_data.get("facility_location"),
            condition_summary=condition_summary,
            damage_remarks=raw_data.get("damage_remarks"),
            handwritten_notes=raw_data.get("handwritten_notes", []) or [],
            stamps_detected=raw_data.get("stamps_detected", []) or [],
            seal_info=seal_info,
            reefer_info=reefer_info,
            unreadable_sections=raw_data.get("unreadable_sections", []) or [],
            field_evidence_map=evidence_map
        )
