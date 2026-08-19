import sys
import time
import statistics
from pathlib import Path
from typing import List, Dict, Any

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from backend.services.document_service import DocumentIntelligenceService
from backend.services.telemetry_engine import DeterministicTelemetryEngine
from backend.services.timeline_engine import DeterministicTimelineFusionEngine
from backend.services.investigation_service import DisputeInvestigationService
from backend.services.security_service import SecurityScreeningService
from backend.services.settlement_service import SettlementService
from backend.services.case_service import CaseService
from backend.models.case import CaseStatus, ShipmentInfo
from backend.models.settlement import (
    CarrierObjectionType,
    InboundCarrierMessage,
    OutboundDraft,
    DraftApprovalStatus
)
from backend.models.investigation import (
    CaseDisputeMetadata,
    DisputeInvestigationRequest
)

# Canonical Sample Data
SAMPLE_TELEMETRY_CSV = """timestamp,latitude,longitude,temp_c,shock_g
2026-08-15 13:00:00,33.7405,-118.2719,-18.2,0.12
2026-08-15 14:00:00,33.7420,-118.2700,-18.0,0.15
2026-08-15 14:30:00,33.7450,-118.2650,-17.9,0.18
2026-08-15 15:30:00,33.8100,-118.1500,-17.5,0.22
2026-08-15 17:15:00,33.8900,-118.0500,-12.4,4.25
2026-08-15 18:00:00,33.9500,-117.9500,-10.1,0.25
"""

SAMPLE_EIR_TEXT = """
APM TERMINALS PIER 400 - LOS ANGELES
EQUIPMENT INTERCHANGE RECEIPT (EIR) - OUTBOUND
--------------------------------------------------
CONTAINER ID: MSKU9082345 (40FT HIGH CUBE REEFER)
CARRIER: APEX DRAYAGE LOGISTICS LLC
DRIVER: R. MARTINEZ (CDL: CA-984210)
TRACTOR / CHASSIS: TR-4421 / CH-8890
DATE & TIME: 2026-08-15 14:30:00 UTC
GATE TRANSACTION: GATE-OUT / INTERCHANGE COMPLETE
SEAL NUMBER: ML-US9082345 (INTACT)
TEMPERATURE SETPOINT: -18.0 C | ACTUAL TEMP: -17.9 C
EQUIPMENT CONDITION: CLEAN / NO DAMAGE NOTED AT GATE-OUT
HANDOVER STATUS: ACCEPTED BY MOTOR CARRIER
"""


def benchmark_pipeline(iterations: int = 5) -> Dict[str, Dict[str, float]]:
    print("=" * 80)
    print(f" SUBROGATE PROTOTYPE PERFORMANCE BENCHMARK ({iterations} Iterations)")
    print("=" * 80)

    doc_service = DocumentIntelligenceService()
    inv_service = DisputeInvestigationService()
    sec_service = SecurityScreeningService()
    case_service = CaseService()
    settle_service = SettlementService(case_service=case_service, security_service=sec_service)

    metrics: Dict[str, List[float]] = {
        "1. Document Text Extraction & Checksum": [],
        "2. Telemetry Parsing & Breach Anomaly Detection": [],
        "3. Deterministic Timeline & Custody Fusion": [],
        "4. Investigator Agent Forensic Assessment": [],
        "5. Google Model Armor Security Gate Screening": [],
        "6. Settlement Agent Carrier Rebuttal Generation": []
    }

    # Create synthetic PDF bytes using reportlab
    import io
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    pdf_buffer = io.BytesIO()
    p = canvas.Canvas(pdf_buffer, pagesize=letter)
    p.drawString(100, 750, "APM TERMINALS PIER 400 - EQUIPMENT INTERCHANGE RECEIPT")
    p.drawString(100, 720, "CONTAINER: MSKU9082345 (40FT REEFER)")
    p.drawString(100, 690, "CARRIER: APEX DRAYAGE LOGISTICS LLC")
    p.drawString(100, 660, "HANDOVER TIME: 2026-08-15 14:30:00 UTC")
    p.drawString(100, 630, "CONDITION: CLEAN / INTACT")
    p.save()
    pdf_bytes = pdf_buffer.getvalue()

    for i in range(iterations):
        # 1. Document Extraction
        t0 = time.perf_counter()
        doc_res = doc_service.process_document(
            file_bytes=pdf_bytes,
            filename="APM_EIR_MSKU9082345.pdf",
            mime_type="application/pdf",
            expected_container_id="MSKU9082345"
        )
        t_doc = (time.perf_counter() - t0) * 1000
        metrics["1. Document Text Extraction & Checksum"].append(t_doc)

        # 2. Telemetry Processing
        t0 = time.perf_counter()
        telemetry = DeterministicTelemetryEngine.process_csv(SAMPLE_TELEMETRY_CSV)
        t_telemetry = (time.perf_counter() - t0) * 1000
        metrics["2. Telemetry Parsing & Breach Anomaly Detection"].append(t_telemetry)

        # 3. Timeline Fusion
        case_meta = CaseDisputeMetadata(
            shipment_id="MSKU9082345",
            carrier_name="Apex Drayage Logistics LLC"
        )
        t0 = time.perf_counter()
        events, windows, overlap = DeterministicTimelineFusionEngine.fuse_timeline(
            telemetry=telemetry,
            extracted_eir=doc_res.extracted_data,
            case_metadata=case_meta
        )
        t_fusion = (time.perf_counter() - t0) * 1000
        metrics["3. Deterministic Timeline & Custody Fusion"].append(t_fusion)

        # 4. Investigator Agent Assessment
        req = DisputeInvestigationRequest(
            case_metadata=case_meta,
            telemetry_csv=SAMPLE_TELEMETRY_CSV,
            eir_raw_text=SAMPLE_EIR_TEXT,
            expected_container_id="MSKU9082345"
        )
        t0 = time.perf_counter()
        assessment_res = inv_service.process_investigation(req)
        t_inv = (time.perf_counter() - t0) * 1000
        metrics["4. Investigator Agent Forensic Assessment"].append(t_inv)

        # Create benchmark case
        case = case_service.create_case(
            shipment_info=ShipmentInfo(container_id="MSKU9082345", carrier_name="Apex Drayage Logistics LLC"),
            actor="BENCHMARK",
            initial_status=CaseStatus.APPROVED
        )

        # 5. Security Screening
        test_draft = OutboundDraft(
            draft_id=f"DRF-BENCH-{i}",
            case_id=case.case_id,
            identified_carrier_objection=CarrierObjectionType.DAMAGE_BEFORE_PICKUP,
            relevant_evidence_citations=[],
            draft_subject="Formal Rebuttal",
            draft_body_markdown="Clean gate receipt confirms cargo in good order at interchange. Telemetry breach at 17:15 UTC.",
            status=DraftApprovalStatus.DRAFT,
            security_check_passed=False,
            next_recommended_action="Transmit recovery package"
        )
        t0 = time.perf_counter()
        sec_report = sec_service.screen_draft(test_draft, case_id=case.case_id)
        t_sec = (time.perf_counter() - t0) * 1000
        metrics["5. Google Model Armor Security Gate Screening"].append(t_sec)

        # 6. Settlement Agent Rebuttal
        inbound = InboundCarrierMessage(
            case_id=case.case_id,
            message_id="MSG-BENCH",
            sender_party="claims@apexdrayage.com",
            subject="Claim Objection",
            body_text="We dispute custody at time of impact.",
            identified_objection=CarrierObjectionType.DISPUTES_CUSTODY
        )
        t0 = time.perf_counter()
        settle_draft = settle_service.generate_draft_response(case.case_id, inbound)
        t_settle = (time.perf_counter() - t0) * 1000
        metrics["6. Settlement Agent Carrier Rebuttal Generation"].append(t_settle)

    # Calculate statistics
    summary: Dict[str, Dict[str, float]] = {}
    for stage, times in metrics.items():
        min_t = round(min(times), 2)
        mean_t = round(statistics.mean(times), 2)
        max_t = round(max(times), 2)
        summary[stage] = {"min_ms": min_t, "mean_ms": mean_t, "max_ms": max_t}
        print(f"{stage:<52} | Mean: {mean_t:>7.2f} ms | Min: {min_t:>7.2f} ms | Max: {max_t:>7.2f} ms")

    print("=" * 80)
    return summary


if __name__ == "__main__":
    benchmark_pipeline(iterations=5)
