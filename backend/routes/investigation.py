import json
import base64
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body, Query
from pydantic import BaseModel, Field

from ..models.investigation import (
    DisputeInvestigationRequest,
    DisputeInvestigationResponse,
    CaseDisputeMetadata,
    FusedTimelineEvent,
    CustodyWindow,
    DeterministicCustodyOverlap
)
from ..models.case import CaseModel, CaseStatus, ShipmentInfo, TelemetryRef
from ..models.telemetry import TelemetryThresholdConfig
from ..services.case_service import CaseService
from ..services.investigation_service import DisputeInvestigationService
from ..services.telemetry_engine import DeterministicTelemetryEngine
from ..services.timeline_engine import DeterministicTimelineFusionEngine
from ..services.async_investigation_worker import AsyncInvestigationWorker, AsyncJobStatus
from ..services.telemetry_simulator import TelemetryEventSimulator, SimulatedTelemetryEvent

router = APIRouter(prefix="/api/investigation", tags=["Forensic Investigation & Assessment"])
_investigation_service = DisputeInvestigationService()
_case_service = CaseService()
_async_worker = AsyncInvestigationWorker()


class AsyncSubmissionResponse(BaseModel):
    case_id: str = Field(..., description="Unique persistent dispute case ID")
    job_id: str = Field(..., description="Asynchronous background job ID")
    status: str = Field(default="PROCESSING", description="Current execution status")
    idempotency_key: str = Field(..., description="Deduplication fingerprint")
    is_duplicate: bool = Field(default=False, description="True if payload matched existing event")
    message: str = Field(..., description="Status summary message")
    tracking_url: str = Field(..., description="URL to poll for updates")


@router.post("/assess-dispute", response_model=DisputeInvestigationResponse)
def assess_dispute_json(payload: DisputeInvestigationRequest) -> DisputeInvestigationResponse:
    """
    Main SubroGate Vertical Slice Endpoint.
    Ingests EIR + Telemetry CSV + Case metadata, reconstructs deterministic timeline,
    and executes Investigator Agent to produce an Evidence-Backed Responsibility Assessment.
    Persists the resulting case in Firestore.
    """
    if not payload.telemetry_csv or not payload.telemetry_csv.strip():
        raise HTTPException(status_code=400, detail="Telemetry CSV data cannot be empty.")

    inv_response = _investigation_service.process_investigation(payload)
    
    # Persist in Firestore
    meta = payload.case_metadata
    case = _case_service.create_case(
        shipment_info=ShipmentInfo(
            container_id=meta.shipment_id,
            commodity=meta.commodity or "General Cargo",
            declared_value_usd=meta.declared_value_usd or 100000.0,
            claimed_loss_usd=meta.claimed_loss_usd or 75000.0,
            origin_facility=meta.origin_facility or "Origin Facility",
            destination_facility=meta.destination_facility or "Destination Facility",
            shipper_name=meta.shipper_name,
            carrier_name=meta.carrier_name,
            consignee_name=meta.consignee_name
        ),
        telemetry_ref=TelemetryRef(
            file_name="telemetry.csv",
            sample_count=len(inv_response.normalized_telemetry.readings) if inv_response.normalized_telemetry else 120,
            ingestion_mode="JSON_DIRECT"
        ),
        actor="USER",
        initial_status=CaseStatus.PROCESSING
    )
    saved_case = _case_service.attach_investigation_result(
        case_id=case.case_id,
        investigation=inv_response,
        actor="INVESTIGATOR_AGENT"
    )
    inv_response.case = saved_case
    return inv_response


@router.post("/assess-multipart", response_model=DisputeInvestigationResponse)
async def assess_dispute_multipart(
    telemetry_file: UploadFile = File(...),
    eir_file: Optional[UploadFile] = File(None),
    shipment_id: str = Form("SHIP-001"),
    shipper_name: str = Form("Origin Shipper Inc."),
    carrier_name: Optional[str] = Form(None),
    consignee_name: Optional[str] = Form(None),
    commodity: Optional[str] = Form(None),
    declared_value_usd: Optional[float] = Form(None),
    claimed_loss_usd: Optional[float] = Form(None),
    origin_facility: Optional[str] = Form(None),
    destination_facility: Optional[str] = Form(None),
    governing_regime: str = Form("Carmack Amendment"),
    default_timezone: Optional[str] = Form(None),
    temp_min_c: Optional[float] = Form(None),
    temp_max_c: Optional[float] = Form(None),
    shock_g_threshold: Optional[float] = Form(4.0)
) -> DisputeInvestigationResponse:
    """
    Multipart file upload endpoint for the vertical slice.
    Processes uploaded EIR & Telemetry files with multimodal document intelligence
    and Gemini assessment, persisting the record in Firestore.
    """
    telemetry_bytes = await telemetry_file.read()
    if len(telemetry_bytes) == 0:
        raise HTTPException(status_code=400, detail="Telemetry CSV file is empty.")

    telemetry_csv_str = telemetry_bytes.decode("utf-8", errors="replace")

    eir_b64: Optional[str] = None
    eir_filename: str = "gate_receipt.pdf"
    eir_mime: str = "application/pdf"

    if eir_file and eir_file.filename:
        eir_bytes = await eir_file.read()
        if len(eir_bytes) > 0:
            eir_b64 = base64.b64encode(eir_bytes).decode("utf-8")
            eir_filename = eir_file.filename
            eir_mime = eir_file.content_type or "application/pdf"

    thresholds = TelemetryThresholdConfig(
        temp_min_c=temp_min_c,
        temp_max_c=temp_max_c,
        shock_g_threshold=shock_g_threshold
    )

    case_metadata = CaseDisputeMetadata(
        shipment_id=shipment_id,
        shipper_name=shipper_name,
        carrier_name=carrier_name,
        consignee_name=consignee_name,
        origin_facility=origin_facility,
        destination_facility=destination_facility,
        commodity=commodity,
        declared_value_usd=declared_value_usd,
        claimed_loss_usd=claimed_loss_usd,
        governing_regime=governing_regime
    )

    request = DisputeInvestigationRequest(
        case_metadata=case_metadata,
        telemetry_csv=telemetry_csv_str,
        default_timezone=default_timezone,
        thresholds=thresholds,
        eir_document_base64=eir_b64,
        eir_filename=eir_filename,
        eir_mime_type=eir_mime
    )

    inv_response = _investigation_service.process_investigation(request)

    # Persist in Firestore
    case = _case_service.create_case(
        shipment_info=ShipmentInfo(
            container_id=shipment_id,
            commodity=commodity or "General Cargo",
            declared_value_usd=declared_value_usd or 100000.0,
            claimed_loss_usd=claimed_loss_usd or 75000.0,
            origin_facility=origin_facility or "Origin Facility",
            destination_facility=destination_facility or "Destination Facility",
            shipper_name=shipper_name,
            carrier_name=carrier_name,
            consignee_name=consignee_name
        ),
        telemetry_ref=TelemetryRef(
            file_name=telemetry_file.filename or "telemetry.csv",
            sample_count=len(inv_response.normalized_telemetry.readings) if inv_response.normalized_telemetry else 120,
            ingestion_mode="MULTIPART_UPLOAD"
        ),
        actor="USER",
        initial_status=CaseStatus.PROCESSING
    )
    saved_case = _case_service.attach_investigation_result(
        case_id=case.case_id,
        investigation=inv_response,
        actor="INVESTIGATOR_AGENT"
    )
    inv_response.case = saved_case
    return inv_response


@router.post("/fuse-timeline")
def fuse_timeline_direct(payload: DisputeInvestigationRequest) -> dict:
    """
    Direct deterministic timeline reconstruction and custody overlap calculation.
    """
    telemetry = DeterministicTelemetryEngine.process_csv(
        csv_text=payload.telemetry_csv,
        thresholds=payload.thresholds,
        default_timezone=payload.default_timezone
    )

    events, windows, overlap = DeterministicTimelineFusionEngine.fuse_timeline(
        telemetry=telemetry,
        extracted_eir=payload.pre_extracted_eir,
        case_metadata=payload.case_metadata,
        default_timezone=payload.default_timezone
    )

    return {
        "shipment_id": payload.case_metadata.shipment_id,
        "timeline_events_count": len(events),
        "timeline_events": [e.model_dump() for e in events],
        "custody_windows": [w.model_dump() for w in windows],
        "deterministic_overlap": overlap.model_dump()
    }


# ==============================================================================
# GENUINE ASYNCHRONOUS & BACKGROUND PROCESSING ENDPOINTS
# ==============================================================================

@router.post("/submit-async", response_model=AsyncSubmissionResponse, status_code=202)
def submit_investigation_async(
    payload: DisputeInvestigationRequest,
    custom_case_id: Optional[str] = Query(None, description="Optional custom case ID"),
    event_id: Optional[str] = Query(None, description="Optional explicit event ID for deduplication")
) -> AsyncSubmissionResponse:
    """
    Submits an investigation for genuine asynchronous background execution.
    Returns immediately with status 'PROCESSING' and tracking details while the backend continues.
    """
    if not payload.telemetry_csv or not payload.telemetry_csv.strip():
        raise HTTPException(status_code=400, detail="Telemetry CSV data cannot be empty.")

    case, job, is_dup = _async_worker.submit_investigation_async(
        request=payload,
        custom_case_id=custom_case_id,
        explicit_event_id=event_id
    )

    msg = "Duplicate event deduplicated. Returning existing case." if is_dup else "Investigation submitted. Processing in background."

    return AsyncSubmissionResponse(
        case_id=case.case_id,
        job_id=job.job_id,
        status="COMPLETED" if case.status.value == "ASSESSMENT_READY" else "PROCESSING",
        idempotency_key=job.idempotency_key,
        is_duplicate=is_dup,
        message=msg,
        tracking_url=f"/api/cases/{case.case_id}"
    )


@router.post("/simulate-telemetry-event", response_model=AsyncSubmissionResponse, status_code=202)
def simulate_telemetry_event(
    event_type: str = Query("SHOCK", description="SHOCK, TEMPERATURE, or CLEAN"),
    container_id: str = Query("MSKU9082345", description="Container unit number"),
    event_id: Optional[str] = Query(None, description="Explicit deterministic event ID for deduplication")
) -> AsyncSubmissionResponse:
    """
    Generates a simulated sensor telemetry event and dispatches background investigation.
    """
    if event_type.upper() == "SHOCK":
        sim_event = TelemetryEventSimulator.generate_shock_breach_event(
            container_id=container_id,
            event_id=event_id
        )
    elif event_type.upper() == "TEMPERATURE" or event_type.upper() == "TEMP":
        sim_event = TelemetryEventSimulator.generate_temperature_excursion_event(
            container_id=container_id,
            event_id=event_id
        )
    else:
        sim_event = TelemetryEventSimulator.generate_nominal_clean_event(
            container_id=container_id,
            event_id=event_id
        )

    req = TelemetryEventSimulator.create_investigation_request_from_event(sim_event)

    case, job, is_dup = _async_worker.submit_investigation_async(
        request=req,
        explicit_event_id=sim_event.event_id
    )

    msg = f"Simulated {sim_event.event_type} event ({sim_event.event_id}) dispatched."
    if is_dup:
        msg = f"Simulated event {sim_event.event_id} was already processed (deduplicated)."

    return AsyncSubmissionResponse(
        case_id=case.case_id,
        job_id=job.job_id,
        status="COMPLETED" if case.status.value == "ASSESSMENT_READY" else "PROCESSING",
        idempotency_key=job.idempotency_key,
        is_duplicate=is_dup,
        message=msg,
        tracking_url=f"/api/cases/{case.case_id}"
    )


@router.post("/cases/{case_id}/retry", response_model=CaseModel)
def retry_failed_investigation(
    case_id: str,
    actor: str = Body("ADJUSTER", embed=True)
) -> CaseModel:
    """
    Retries asynchronous processing for a failed or interrupted investigation.
    """
    try:
        updated_case, job = _async_worker.retry_case(case_id=case_id, actor=actor)
        return updated_case
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@router.get("/jobs/{job_id}")
def get_async_job_status(job_id: str) -> dict:
    """
    Retrieves status and progress of an asynchronous job.
    """
    job = _async_worker.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job with ID '{job_id}' not found.")
    return job.to_dict()


@router.get("/jobs/by-case/{case_id}")
def get_async_job_by_case(case_id: str) -> dict:
    """
    Retrieves the active or recent asynchronous job for a case.
    """
    job = _async_worker.get_job_by_case(case_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"No background job found for case '{case_id}'.")
    return job.to_dict()
