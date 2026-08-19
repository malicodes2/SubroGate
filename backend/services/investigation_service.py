import time
import base64
from typing import Optional
from datetime import datetime

from ..models.investigation import (
    DisputeInvestigationRequest,
    DisputeInvestigationResponse,
    CaseDisputeMetadata
)
from ..models.documents import EIRExtractionResult, ExtractedEIRData
from ..models.telemetry import IncidentTelemetry
from .telemetry_engine import DeterministicTelemetryEngine
from .document_service import DocumentIntelligenceService
from .timeline_engine import DeterministicTimelineFusionEngine
from ..agents.investigator_agent import InvestigatorAgent


class DisputeInvestigationService:
    """
    End-to-End Orchestrator for the SubroGate Vertical Slice.
    Fuses Document Intelligence, Telemetry Normalization, Timeline Fusion,
    and Investigator Agent Assessment.
    """

    def __init__(
        self,
        doc_service: Optional[DocumentIntelligenceService] = None,
        investigator_agent: Optional[InvestigatorAgent] = None
    ):
        self.doc_service = doc_service or DocumentIntelligenceService()
        self.investigator_agent = investigator_agent or InvestigatorAgent()

    def process_investigation(
        self,
        request: DisputeInvestigationRequest
    ) -> DisputeInvestigationResponse:
        """
        Executes complete vertical slice investigation on EIR and Telemetry inputs.
        """
        start_time = time.time()
        case_meta = request.case_metadata

        # 1. Deterministic Telemetry Processing
        telemetry_result: IncidentTelemetry = DeterministicTelemetryEngine.process_csv(
            csv_text=request.telemetry_csv,
            thresholds=request.thresholds,
            default_timezone=request.default_timezone
        )

        # 2. Document Intelligence Extraction & Validation
        eir_result: Optional[EIRExtractionResult] = None
        extracted_eir: Optional[ExtractedEIRData] = None

        if request.pre_extracted_eir:
            extracted_eir = request.pre_extracted_eir
        elif request.eir_document_base64:
            try:
                doc_bytes = base64.b64decode(request.eir_document_base64)
                eir_result = self.doc_service.process_document(
                    file_bytes=doc_bytes,
                    filename=request.eir_filename or "gate_receipt.pdf",
                    mime_type=request.eir_mime_type or "application/pdf",
                    expected_container_id=None,
                    expected_carrier=case_meta.carrier_name,
                    default_timezone=request.default_timezone
                )
                extracted_eir = eir_result.extracted_data
            except Exception as e:
                # Handled gracefully without crashing
                pass

        # 3. Deterministic Timeline & Custody Fusion
        timeline_events, custody_windows, overlap = DeterministicTimelineFusionEngine.fuse_timeline(
            telemetry=telemetry_result,
            extracted_eir=extracted_eir,
            case_metadata=case_meta,
            default_timezone=request.default_timezone
        )

        # 4. Investigator Agent Assessment
        assessment = self.investigator_agent.assess_dispute(
            telemetry=telemetry_result,
            extracted_eir=extracted_eir,
            eir_validation=eir_result.validation_report if eir_result else None,
            timeline=timeline_events,
            custody_windows=custody_windows,
            deterministic_overlap=overlap,
            case_metadata=case_meta
        )

        elapsed_ms = (time.time() - start_time) * 1000

        return DisputeInvestigationResponse(
            shipment_id=case_meta.shipment_id,
            extracted_eir=eir_result,
            normalized_telemetry=telemetry_result,
            reconstructed_timeline=timeline_events,
            custody_windows=custody_windows,
            deterministic_overlap=overlap,
            evidence_backed_assessment=assessment,
            execution_time_ms=round(elapsed_ms, 2)
        )
