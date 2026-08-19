import json
import logging
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .base import BaseForensicAgent
from ..models.investigation import (
    EvidenceBackedAssessment,
    DeterministicCustodyOverlap,
    LegalFrameworkReference,
    EvidenceCitation,
    CustodyRole,
    CaseDisputeMetadata,
    CustodyWindow,
    FusedTimelineEvent
)
from ..models.telemetry import IncidentTelemetry
from ..models.documents import ExtractedEIRData, HandoverCondition, DocumentValidationReport

logger = logging.getLogger("subrogate.agents.investigator")

# Structured Statutory Source Material Library
STATUTORY_SOURCES: Dict[str, LegalFrameworkReference] = {
    "Carmack Amendment": LegalFrameworkReference(
        statutory_regime="Carmack Amendment",
        citation="49 U.S.C. § 14706",
        rule_summary=(
            "Imposes strict liability upon motor carriers for actual loss or injury to property occurring "
            "during interstate transit under a bill of lading. A prima facie claim requires showing: "
            "(1) cargo delivered to carrier in good condition, (2) cargo arrived damaged at destination, "
            "and (3) measurable damages."
        ),
        burden_of_proof_standard=(
            "Once prima facie burden is met, the burden shifts to the carrier to prove absence of negligence "
            "and that damage resulted solely from one of five common law statutory exceptions: Act of God, "
            "public enemy, act of shipper/inherent vice, public authority, or natural shrinkage."
        ),
        source_document="U.S. Interstate Commerce Act (49 U.S.C. § 14706)"
    ),
    "COGSA": LegalFrameworkReference(
        statutory_regime="Carriage of Goods by Sea Act (COGSA)",
        citation="46 U.S.C. § 30701 note (formerly 46 U.S.C. app. §§ 1300-1315)",
        rule_summary=(
            "Governs ocean carrier contracts of carriage tackle-to-tackle. Carrier must exercise due diligence "
            "to make the vessel seaworthy and properly handle, carry, keep, care for, and discharge goods."
        ),
        burden_of_proof_standard="Carrier liability subject to $500 per customary freight unit package limitation unless declared value paid.",
        source_document="U.S. Maritime Carriage Law (46 U.S.C. § 30701)"
    ),
    "CMR": LegalFrameworkReference(
        statutory_regime="CMR Convention",
        citation="UN Convention on the Contract for the International Carriage of Goods by Road (1956)",
        rule_summary="Carrier is liable for total or partial loss and damage occurring between taking over and delivery.",
        burden_of_proof_standard="Carrier relief requires proving circumstances which the carrier could not avoid and the consequences of which it was unable to prevent.",
        source_document="CMR International Convention (Geneva, 1956)"
    )
}

INVESTIGATOR_SYSTEM_INSTRUCTION = """
You are SubroGate's Senior Cargo Dispute Forensic Investigator.
Your task is to review the reconstructed chronological timeline, deterministic telemetry breaches, Equipment Interchange Receipts (EIR), and case facts to produce an Evidence-Backed Responsibility Assessment.

STRICT LEGAL AND FORENSIC BOUNDARIES:
1. NEVER USE FORBIDDEN PHRASES:
   - Do NOT say "Legal ruling"
   - Do NOT say "Binding liability determination"
   - Do NOT say "Guaranteed legal liability"
   Instead, formulate your findings as an "Evidence-Backed Responsibility Assessment".
2. NO HALLUCINATION OF EVIDENCE:
   - Reason ONLY over the provided deterministic timeline, sensor readings, EIR data, and statutory reference sources.
   - Do NOT invent timestamps, G-force numbers, temperature values, or citations.
3. STRUCTURED PROVENANCE:
   - Every factual assertion MUST include a supporting evidence citation referencing either the EIR document, telemetry log row, or statutory source.
4. CONFLICTING EVIDENCE & UNCERTAINTY:
   - Explicitly identify contradictory evidence (e.g. clean EIR condition remarks vs severe sensor impact shocks).
   - Surface all data gaps, unreadable sections, or missing timezone offsets in 'uncertainties_and_gaps'.
5. RESPECT DETERMINISTIC OVERLAP:
   - The deterministic custody window overlap calculation provided in the prompt is your primary temporal anchor. Analyze whether physical evidence supports or complicates this baseline calculation.

OUTPUT FORMAT:
Return ONLY valid JSON matching this schema:
{
  "potentially_responsible_party": "string (entity name)",
  "potentially_responsible_role": "SHIPPER | DRAYAGE_ORIGIN | ORIGIN_TERMINAL | OCEAN_CARRIER | RAIL_CARRIER | DESTINATION_TERMINAL | DRAYAGE_DESTINATION | CONSIGNEE | UNKNOWN",
  "confidence_score": float (0.0 to 1.0),
  "supporting_evidence": [
    {
      "citation_id": "CIT-01",
      "source_type": "EIR_DOCUMENT | TELEMETRY_LOG | CASE_METADATA | STATUTORY_SOURCE",
      "source_reference": "string",
      "verbatim_quote_or_datapoint": "string",
      "relevance_explanation": "string"
    }
  ],
  "conflicting_evidence": [
    {
      "citation_id": "CIT-02",
      "source_type": "EIR_DOCUMENT | TELEMETRY_LOG | CASE_METADATA | STATUTORY_SOURCE",
      "source_reference": "string",
      "verbatim_quote_or_datapoint": "string",
      "relevance_explanation": "string"
    }
  ],
  "contractual_citations": ["citation 1", ...],
  "uncertainties_and_gaps": ["gap 1", ...],
  "recommended_recovery_action": "Actionable next steps for subrogation claims adjuster",
  "human_review_required": true
}
"""


from ..observability.tracer import trace_span

class InvestigatorAgent(BaseForensicAgent):
    """
    Google ADK & Vertex AI / GenAI compatible Forensic Investigator Agent.
    Evaluates evidence, timeline fusion, and statutory frameworks to produce
    an audit-ready Evidence-Backed Responsibility Assessment.
    """

    def __init__(self, agent_name: str = "ForensicInvestigatorAgent"):
        super().__init__(agent_name=agent_name)

    def assess_dispute(
        self,
        telemetry: IncidentTelemetry,
        extracted_eir: Optional[ExtractedEIRData],
        eir_validation: Optional[DocumentValidationReport],
        timeline: List[FusedTimelineEvent],
        custody_windows: List[CustodyWindow],
        deterministic_overlap: DeterministicCustodyOverlap,
        case_metadata: CaseDisputeMetadata
    ) -> EvidenceBackedAssessment:
        """
        Executes evidence assessment via Gemini or deterministic fallback.
        """
        case_id = getattr(case_metadata, "case_id", getattr(case_metadata, "shipment_id", "UNKNOWN"))
        with trace_span(
            name="Forensic Investigator Assessment Synthesis",
            category="INVESTIGATOR_AGENT",
            attributes={
                "case_id": case_id,
                "agent.name": self.agent_name,
                "model.name": self.model_name,
                "is_online": self.is_online
            }
        ) as span:
            statutory_regime = case_metadata.governing_regime or "Carmack Amendment"
            legal_ref = STATUTORY_SOURCES.get(statutory_regime, STATUTORY_SOURCES["Carmack Amendment"])

            # Try live model execution if client is online
            assessment = None
            if self.is_online:
                try:
                    assessment = self._execute_agent_reasoning(
                        telemetry=telemetry,
                        extracted_eir=extracted_eir,
                        eir_validation=eir_validation,
                        timeline=timeline,
                        custody_windows=custody_windows,
                        deterministic_overlap=deterministic_overlap,
                        case_metadata=case_metadata,
                        legal_ref=legal_ref
                    )
                except Exception as e:
                    logger.warning(f"Investigator agent model execution failed: {e}. Executing deterministic fallback.")

            # Fallback to deterministic assessment if model did not return valid result
            if not assessment:
                assessment = self._generate_deterministic_assessment(
                    telemetry=telemetry,
                    extracted_eir=extracted_eir,
                    eir_validation=eir_validation,
                    timeline=timeline,
                    deterministic_overlap=deterministic_overlap,
                    case_metadata=case_metadata,
                    legal_ref=legal_ref
                )

            span.set_attribute("assessment.responsible_party", assessment.potentially_responsible_party.value if hasattr(assessment.potentially_responsible_party, 'value') else str(assessment.potentially_responsible_party))
            span.set_attribute("assessment.confidence_score", assessment.confidence_score)

            return assessment

    def _execute_agent_reasoning(
        self,
        telemetry: IncidentTelemetry,
        extracted_eir: Optional[ExtractedEIRData],
        eir_validation: Optional[DocumentValidationReport],
        timeline: List[FusedTimelineEvent],
        custody_windows: List[CustodyWindow],
        deterministic_overlap: DeterministicCustodyOverlap,
        case_metadata: CaseDisputeMetadata,
        legal_ref: LegalFrameworkReference
    ) -> Optional[EvidenceBackedAssessment]:
        """Prompts Gemini with structured evidence payload."""
        prompt_payload = {
            "case_metadata": case_metadata.model_dump(),
            "deterministic_overlap": deterministic_overlap.model_dump(),
            "telemetry_breaches": [b.model_dump() for b in telemetry.breaches],
            "telemetry_quality": telemetry.data_quality.model_dump(),
            "extracted_eir": extracted_eir.model_dump() if extracted_eir else None,
            "eir_validation": eir_validation.model_dump() if eir_validation else None,
            "timeline_events_sample": [e.model_dump() for e in timeline[:15]],
            "custody_windows": [w.model_dump() for w in custody_windows],
            "statutory_source_material": legal_ref.model_dump()
        }

        prompt = (
            "Analyze the attached cargo transit dispute evidence and produce an Evidence-Backed Responsibility Assessment.\n"
            f"Evidence Context: {json.dumps(prompt_payload, default=str)}"
        )

        raw_json = self.execute_structured(
            prompt=prompt,
            system_instruction=INVESTIGATOR_SYSTEM_INSTRUCTION
        )

        if not raw_json:
            return None

        # Parse supporting evidence citations
        supporting_citations: List[EvidenceCitation] = []
        for cit in raw_json.get("supporting_evidence", []):
            if isinstance(cit, dict):
                supporting_citations.append(
                    EvidenceCitation(
                        citation_id=cit.get("citation_id", f"CIT-{uuid.uuid4().hex[:4]}"),
                        source_type=cit.get("source_type", "EIR_DOCUMENT"),
                        source_reference=cit.get("source_reference", "Evidence Record"),
                        verbatim_quote_or_datapoint=cit.get("verbatim_quote_or_datapoint", ""),
                        relevance_explanation=cit.get("relevance_explanation", "")
                    )
                )

        conflicting_citations: List[EvidenceCitation] = []
        for cit in raw_json.get("conflicting_evidence", []):
            if isinstance(cit, dict):
                conflicting_citations.append(
                    EvidenceCitation(
                        citation_id=cit.get("citation_id", f"CIT-{uuid.uuid4().hex[:4]}"),
                        source_type=cit.get("source_type", "EIR_DOCUMENT"),
                        source_reference=cit.get("source_reference", "Evidence Record"),
                        verbatim_quote_or_datapoint=cit.get("verbatim_quote_or_datapoint", ""),
                        relevance_explanation=cit.get("relevance_explanation", "")
                    )
                )

        role_str = str(raw_json.get("potentially_responsible_role", "UNKNOWN")).upper()
        try:
            responsible_role = CustodyRole(role_str)
        except ValueError:
            responsible_role = CustodyRole.UNKNOWN

        return EvidenceBackedAssessment(
            shipment_id=case_metadata.shipment_id,
            assessment_timestamp_utc=datetime.now(timezone.utc),
            potentially_responsible_party=raw_json.get("potentially_responsible_party", deterministic_overlap.culpable_party),
            potentially_responsible_role=responsible_role if responsible_role != CustodyRole.UNKNOWN else deterministic_overlap.culpable_role,
            confidence_score=float(raw_json.get("confidence_score", deterministic_overlap.overlap_confidence)),
            deterministic_overlap=deterministic_overlap,
            supporting_evidence=supporting_citations,
            conflicting_evidence=conflicting_citations,
            applicable_framework=legal_ref,
            contractual_citations=raw_json.get("contractual_citations", []),
            uncertainties_and_gaps=raw_json.get("uncertainties_and_gaps", []),
            recommended_recovery_action=raw_json.get("recommended_recovery_action", "Proceed with formal subrogation claim package."),
            human_review_required=bool(raw_json.get("human_review_required", True))
        )

    def _generate_deterministic_assessment(
        self,
        telemetry: IncidentTelemetry,
        extracted_eir: Optional[ExtractedEIRData],
        eir_validation: Optional[DocumentValidationReport],
        timeline: List[FusedTimelineEvent],
        deterministic_overlap: DeterministicCustodyOverlap,
        case_metadata: CaseDisputeMetadata,
        legal_ref: LegalFrameworkReference
    ) -> EvidenceBackedAssessment:
        """
        Pure deterministic evidence synthesis when running offline.
        Ensures 100% test reliability and transparency without LLM dependency.
        """
        supporting: List[EvidenceCitation] = []
        conflicting: List[EvidenceCitation] = []
        uncertainties: List[str] = []

        # 1. Evidence Citations for Breaches
        for breach in telemetry.breaches:
            supporting.append(
                EvidenceCitation(
                    citation_id=f"CIT-TEL-{breach.breach_id}",
                    source_type="TELEMETRY_LOG",
                    source_reference=f"Breach ID {breach.breach_id}",
                    verbatim_quote_or_datapoint=(
                        f"{breach.breach_type.value}: Peak {breach.peak_value:.2f} (Threshold: {breach.threshold_value:.2f}), "
                        f"Duration {breach.duration_seconds/60:.1f}m starting {breach.breach_start.strftime('%Y-%m-%d %H:%M:%S UTC')}"
                    ),
                    timestamp_utc=breach.breach_start,
                    relevance_explanation="Proves physical cargo threshold violation occurred during transit."
                )
            )

        # 2. Evidence Citations for Document Handovers
        if extracted_eir:
            if extracted_eir.raw_timestamp_str:
                supporting.append(
                    EvidenceCitation(
                        citation_id="CIT-EIR-TIME",
                        source_type="EIR_DOCUMENT",
                        source_reference="Equipment Interchange Receipt",
                        verbatim_quote_or_datapoint=f"Handover timestamp: '{extracted_eir.raw_timestamp_str}'",
                        timestamp_utc=eir_validation.normalized_timestamp_utc if eir_validation else None,
                        relevance_explanation="Establishes Care, Custody, and Control transfer boundary."
                    )
                )

            # Check for conflicting evidence (Clean EIR vs Sensor Shock or Damage Remarks)
            if extracted_eir.condition_summary == HandoverCondition.CLEAN and telemetry.breaches:
                conflicting.append(
                    EvidenceCitation(
                        citation_id="CIT-EIR-CONFLICT-CLEAN",
                        source_type="EIR_DOCUMENT",
                        source_reference="EIR Condition Stamp",
                        verbatim_quote_or_datapoint="Condition recorded as 'CLEAN / NO DAMAGE'",
                        timestamp_utc=eir_validation.normalized_timestamp_utc if eir_validation else None,
                        relevance_explanation=(
                            "EIR indicates clean handover without exceptions, whereas telemetry records "
                            "significant physical violation during the custody period."
                        )
                    )
                )

            if extracted_eir.damage_remarks:
                supporting.append(
                    EvidenceCitation(
                        citation_id="CIT-EIR-REMARKS",
                        source_type="EIR_DOCUMENT",
                        source_reference="EIR Damage Remarks",
                        verbatim_quote_or_datapoint=extracted_eir.damage_remarks,
                        timestamp_utc=eir_validation.normalized_timestamp_utc if eir_validation else None,
                        relevance_explanation="Physical damage or condition exception recorded at gate interchange."
                    )
                )

        # 3. Data Gaps and Uncertainties
        if not telemetry.breaches:
            uncertainties.append("No sensor threshold breaches were detected in the provided telemetry log.")
        if eir_validation and not eir_validation.is_timezone_explicit:
            uncertainties.append(
                "EIR document timestamp lacked an explicit timezone offset; normalized assuming default timezone."
            )
        if eir_validation and eir_validation.errors:
            uncertainties.extend(eir_validation.errors)
        if not extracted_eir:
            uncertainties.append("No EIR document was provided; custody windows estimated from telemetry limits.")

        # 4. Recommended Recovery Action
        if deterministic_overlap.has_breach and deterministic_overlap.culpable_party:
            recommended_action = (
                f"Issue formal Notice of Subrogation Claim against {deterministic_overlap.culpable_party} "
                f"under {legal_ref.statutory_regime} ({legal_ref.citation}) based on prima facie proof "
                f"of loss during their verified custody interval."
            )
        else:
            recommended_action = (
                "Review additional bill of lading and surveyor reports; current evidence is insufficient "
                "to establish carrier liability."
            )

        return EvidenceBackedAssessment(
            shipment_id=case_metadata.shipment_id,
            assessment_timestamp_utc=datetime.now(timezone.utc),
            potentially_responsible_party=deterministic_overlap.culpable_party,
            potentially_responsible_role=deterministic_overlap.culpable_role,
            confidence_score=deterministic_overlap.overlap_confidence,
            deterministic_overlap=deterministic_overlap,
            supporting_evidence=supporting,
            conflicting_evidence=conflicting,
            applicable_framework=legal_ref,
            contractual_citations=[
                f"{legal_ref.statutory_regime} ({legal_ref.citation})",
                "Uniform Intermodal Interchange and Facilities Access Agreement (UIIA) § E.1"
            ],
            uncertainties_and_gaps=uncertainties,
            recommended_recovery_action=recommended_action,
            human_review_required=True
        )
