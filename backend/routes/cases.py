from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query, Body, Depends
from pydantic import BaseModel, Field

from ..models.case import (
    CaseModel,
    CaseStatus,
    ShipmentInfo,
    SourceDocumentRef,
    TelemetryRef,
    HumanApprovalEvent,
    NegotiationMessage,
    SettlementState,
    AuditEvent
)
from ..services.case_service import CaseService
from ..services.case_repository import CaseNotFoundError, ConcurrencyConflictError
from ..utils.auth import verify_agent_identity

router = APIRouter(prefix="/api/cases", tags=["Case State & Management"])
_case_service = CaseService()


class CreateCaseRequest(BaseModel):
    shipment_info: Optional[ShipmentInfo] = None
    document_refs: Optional[List[SourceDocumentRef]] = None
    telemetry_ref: Optional[TelemetryRef] = None
    actor: str = "USER"
    initial_status: CaseStatus = CaseStatus.NEW
    custom_case_id: Optional[str] = None


class StatusTransitionRequest(BaseModel):
    new_status: CaseStatus
    actor: str = "USER"
    reason: Optional[str] = None
    expected_version: Optional[int] = None


class AppendAuditRequest(BaseModel):
    event_type: str
    description: str
    actor: str = "SYSTEM"
    metadata: Optional[Dict[str, Any]] = None
    expected_version: Optional[int] = None


class AppendNegotiationRequest(BaseModel):
    message: NegotiationMessage
    actor: str = "ADJUSTER"
    expected_version: Optional[int] = None


class HumanApprovalRequest(BaseModel):
    approval: HumanApprovalEvent
    actor: str = "ADJUSTER"
    expected_version: Optional[int] = None


@router.post("", response_model=CaseModel, status_code=201, dependencies=[Depends(verify_agent_identity)])
def create_case(payload: CreateCaseRequest) -> CaseModel:
    """
    Initializes a new persistent dispute case in Firestore.
    """
    return _case_service.create_case(
        shipment_info=payload.shipment_info,
        document_refs=payload.document_refs,
        telemetry_ref=payload.telemetry_ref,
        actor=payload.actor,
        initial_status=payload.initial_status,
        custom_case_id=payload.custom_case_id
    )


@router.get("/{case_id}", response_model=CaseModel)
def get_case(case_id: str) -> CaseModel:
    """
    Retrieves a persistent case by unique Case ID.
    """
    case = _case_service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found.")
    return case


@router.get("", response_model=List[CaseModel])
def list_cases(
    limit: int = Query(default=50, ge=1, le=200),
    status: Optional[CaseStatus] = Query(default=None)
) -> List[CaseModel]:
    """
    Lists recent dispute cases with optional status filter.
    """
    return _case_service.list_cases(limit=limit, status=status)


@router.patch("/{case_id}/status", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def transition_case_status(
    case_id: str,
    payload: StatusTransitionRequest
) -> CaseModel:
    """
    Transitions case status with optimistic concurrency checking and audit logging.
    """
    try:
        return _case_service.transition_status(
            case_id=case_id,
            new_status=payload.new_status,
            actor=payload.actor,
            reason=payload.reason,
            expected_version=payload.expected_version
        )
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{case_id}/audit-events", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def append_audit_event(
    case_id: str,
    payload: AppendAuditRequest
) -> CaseModel:
    """
    Appends an immutable audit event to the case history.
    """
    try:
        return _case_service.append_audit_event(
            case_id=case_id,
            event_type=payload.event_type,
            description=payload.description,
            actor=payload.actor,
            metadata=payload.metadata,
            expected_version=payload.expected_version
        )
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{case_id}/negotiation", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def append_negotiation_message(
    case_id: str,
    payload: AppendNegotiationRequest
) -> CaseModel:
    """
    Appends a communication message or demand notice to the case negotiation history.
    """
    try:
        return _case_service.append_negotiation_message(
            case_id=case_id,
            message=payload.message,
            actor=payload.actor,
            expected_version=payload.expected_version
        )
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{case_id}/approve", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def approve_case_liability(
    case_id: str,
    payload: HumanApprovalRequest
) -> CaseModel:
    """
    Human claims adjuster checkpoint to lock liability allocation and grant approval.
    """
    try:
        return _case_service.record_human_approval(
            case_id=case_id,
            approval=payload.approval,
            actor=payload.actor,
            expected_version=payload.expected_version
        )
    except CaseNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ConcurrencyConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/{case_id}/retry", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def retry_case_processing(
    case_id: str,
    actor: str = Body("ADJUSTER", embed=True)
) -> CaseModel:
    """
    Retries asynchronous processing for a failed or stuck case.
    """
    from ..services.async_investigation_worker import AsyncInvestigationWorker
    worker = AsyncInvestigationWorker()
    try:
        updated_case, job = worker.retry_case(case_id=case_id, actor=actor)
        return updated_case
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retry failed: {str(e)}")


@router.post("/{case_id}/reanalyze", response_model=CaseModel, dependencies=[Depends(verify_agent_identity)])
def reanalyze_case(
    case_id: str,
    corrections: Dict[str, Any] = Body(...)
) -> CaseModel:
    """
    Reanalyzes the timeline and assessment based on human corrections to extracted data.
    """
    case = _case_service.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")

    extracted = case.extracted_custody_events or {}
    new_timestamp_str = corrections.get("handover_timestamp_utc")

    # Update human corrections
    case.human_corrections = corrections
    case.status = CaseStatus.ASSESSMENT_READY
    
    if new_timestamp_str and case.normalized_timeline:
        try:
            from datetime import datetime
            new_dt = datetime.fromisoformat(new_timestamp_str.replace("Z", "+00:00"))
            
            # Find and update EIR handover event
            breach_dt = None
            for event in case.normalized_timeline:
                if event.get("event_type") == "EIR_HANDOVER":
                    event["timestamp_utc"] = new_timestamp_str
                if event.get("is_breach") or event.get("event_type") == "TELEMETRY_BREACH":
                    ts_str = event.get("timestamp_utc")
                    if ts_str:
                        breach_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            
            # Recalculate assessment based on new timeline
            if breach_dt and case.assessment:
                shipper = getattr(case.shipment_info, "shipper_name", "Origin Shipper") if case.shipment_info else "Origin Shipper"
                carrier = getattr(case.shipment_info, "carrier_name", "Apex Drayage Logistics LLC") if case.shipment_info else "Apex Drayage Logistics LLC"
                if breach_dt < new_dt:
                    case.assessment["potentially_responsible_party"] = shipper or "Origin Shipper"
                    case.assessment["evidence_supporting_assessment"] = [
                        f"Human override established handover at {new_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
                        f"Breach occurred at {breach_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}, which is BEFORE handover.",
                        "Custody resided with releasing party."
                    ]
                else:
                    case.assessment["potentially_responsible_party"] = carrier or "Apex Drayage Logistics LLC"
                    case.assessment["evidence_supporting_assessment"] = [
                        f"Human override established handover at {new_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}.",
                        f"Breach occurred at {breach_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}, which is AFTER handover.",
                        "Custody resided with receiving carrier."
                    ]
        except Exception as e:
            logger.error(f"Error parsing timestamp in case reanalysis: {e}")

    updated_case = _case_service.repository.update(
        case_id=case.case_id,
        updates={
            "human_corrections": case.human_corrections,
            "normalized_timeline": case.normalized_timeline,
            "assessment": case.assessment,
            "status": case.status
        }
    )
    return updated_case


@router.post("/demo/load-clean", response_model=CaseModel)
def load_demo_clean_case() -> CaseModel:
    """
    Generates a full ready-to-investigate clean demo case with real EIR, telemetry,
    fused timeline, and forensic investigator assessment.
    """
    case_id = "CASE-2026-DEMO-MSKU"
    
    # Reset existing demo case if present
    _case_service.repository.delete(case_id)
    
    shipment = ShipmentInfo(
        container_id="MSKU9082345",
        commodity="Frozen Pharmaceutical Vaccines",
        declared_value_usd=100000.0,
        claimed_loss_usd=75000.0,
        origin_facility="APM Terminals Pier 400 Los Angeles, CA",
        destination_facility="Midwest Health Distribution Chicago, IL",
        shipper_name="Pacific Pharma Global Inc.",
        carrier_name="Apex Drayage Logistics LLC",
        consignee_name="Midwest Cold Chain Medical Inc.",
        bill_of_lading_number="BOL-MSK-984210"
    )
    
    doc_ref = SourceDocumentRef(
        document_id="DOC-EIR-001",
        filename="APM_Pier400_GateReceipt_MSKU9082345.pdf",
        mime_type="application/pdf",
        sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1048576,
        document_type="EIR"
    )
    
    tel_ref = TelemetryRef(
        device_id="SENS-LOG-8891",
        total_readings_count=120,
        breaches_detected_count=2,
        earliest_reading_utc=datetime(2026, 8, 15, 8, 0, 0, tzinfo=timezone.utc),
        latest_reading_utc=datetime(2026, 8, 16, 11, 0, 0, tzinfo=timezone.utc),
        has_critical_shock=True,
        has_temp_excursion=True
    )
    
    case = _case_service.create_case(
        shipment_info=shipment,
        document_refs=[doc_ref],
        telemetry_ref=tel_ref,
        actor="DEMO_LOADER",
        initial_status=CaseStatus.ASSESSMENT_READY,
        custom_case_id=case_id
    )
    
    # Populate EIR Extraction snapshot
    eir_data = {
        "container_id": "MSKU9082345",
        "iso_check_digit_valid": True,
        "gate_event_type": "OUTGATE_LOADED",
        "handover_timestamp_utc": "2026-08-15T14:30:00Z",
        "issuing_facility": "APM Terminals Pier 400",
        "releasing_party": "APM Terminals Pacific",
        "receiving_party": "Apex Drayage Logistics LLC",
        "equipment_condition": "CLEAN",
        "damage_remarks": "CLEAN - NO VISIBLE EXTERNAL DAMAGE",
        "extraction_status": "PASS",
        "source_page": 1,
        "sha256_fingerprint": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
    
    # Populate Normalized Timeline
    timeline = [
        {
            "event_id": "EVT-01",
            "timestamp_utc": "2026-08-15T08:00:00Z",
            "event_type": "CONTAINER_INGATE",
            "location_name": "APM Terminals Pier 400 Los Angeles, CA",
            "active_custody_holder": "APM Terminals",
            "role": "origin_terminal",
            "description": "Container ingate and staged on reefer power plug at terminal.",
            "is_breach": False,
            "evidence_source": "Terminal TOS Log"
        },
        {
            "event_id": "EVT-02",
            "timestamp_utc": "2026-08-15T14:30:00Z",
            "event_type": "EIR_HANDOVER",
            "location_name": "APM Terminals Outgate Lane 4",
            "active_custody_holder": "Apex Drayage Logistics LLC",
            "role": "drayage_origin",
            "description": "Origin Gate Handover to Apex Drayage. Condition: CLEAN.",
            "is_breach": False,
            "is_relevant_handover": True,
            "evidence_source": "Signed EIR Receipt #9842"
        },
        {
            "event_id": "EVT-03",
            "timestamp_utc": "2026-08-15T15:00:00Z",
            "event_type": "ROAD_TRANSIT_DEPARTURE",
            "location_name": "Interstate 15 Northbound Corridor",
            "active_custody_holder": "Apex Drayage Logistics LLC",
            "role": "drayage_origin",
            "description": "Carrier unit en route to rail intermodal terminal.",
            "is_breach": False,
            "evidence_source": "GPS Telemetry"
        },
        {
            "event_id": "EVT-04",
            "timestamp_utc": "2026-08-15T17:15:00Z",
            "event_type": "TELEMETRY_BREACH",
            "location_name": "Barstow Highway Transit Point",
            "active_custody_holder": "Apex Drayage Logistics LLC",
            "role": "drayage_origin",
            "description": "CRITICAL BREACH: 4.2G Severe Physical Shock & Reefer Temperature Excursion to +12.4°C.",
            "is_breach": True,
            "is_earliest_breach": True,
            "evidence_source": "NIST Calibrated IoT Logger #8891"
        },
        {
            "event_id": "EVT-05",
            "timestamp_utc": "2026-08-16T11:00:00Z",
            "event_type": "DELIVERY_INGATE",
            "location_name": "Midwest Cold Chain Medical Chicago, IL",
            "active_custody_holder": "Midwest Cold Chain Medical Inc.",
            "role": "consignee",
            "description": "Delivery ingate. Consignee rejected load due to high temp logger alert.",
            "is_breach": False,
            "evidence_source": "Destination Delivery Receipt"
        }
    ]
    
    # Populate Investigator Assessment
    assessment = {
        "potentially_responsible_party": "Apex Drayage Logistics LLC (Receiving Motor Carrier)",
        "responsibility_confidence": 0.94,
        "evidence_supporting_assessment": [
            "Signed Gate Interchange Receipt (EIR) confirms container MSKU9082345 was inspected and released to Apex Drayage in clean condition with no damage at 14:30 UTC.",
            "Calibrated IoT sensor telemetry confirms 4.2G shock and reefer thermal excursion occurred at 17:15 UTC (+2.75 hours after gate interchange while under Apex Drayage physical care).",
            "Temporal custody fusion confirms carrier held exclusive Care, Custody, and Control at the moment of earliest recorded breach."
        ],
        "conflicting_evidence": [
            "Carrier driver verbally alleged unit was warm prior to gate outgate; however, driver signed clean interchange receipt without noting exception, legally waiving pre-existing defect defenses."
        ],
        "uncertainties": [
            "Minor 15-minute GPS drift between Barstow cell towers does not impact continuous internal accelerometer logging."
        ],
        "applicable_legal_framework": [
            {
                "framework_name": "Carmack Amendment (49 U.S.C. § 14706)",
                "governing_law_citation": "49 U.S.C. § 14706",
                "key_legal_principle": "Establishes strict prima facie liability on motor carriers for loss/damage during transit upon proof of delivery in good condition and damage at delivery."
            },
            {
                "framework_name": "Uniform Intermodal Interchange Agreement (UIIA Section E.2)",
                "governing_law_citation": "UIIA Sec. E.2",
                "key_legal_principle": "Motor carrier assumes full Care, Custody, and Control upon signing gate interchange receipt at ocean/rail terminal."
            }
        ],
        "recommended_recovery_action": "Issue formal Subrogation Demand Letter to Apex Drayage Claims Dept for full claimed loss of $75,000.00 USD under 49 U.S.C. § 14706."
    }
    
    settlement_state = SettlementState(
        target_recovery_usd=75000.0,
        acceptable_settlement_floor_usd=60000.0,
        recommended_posture="FIRM_ASSERTIVE",
        settlement_status="PENDING_APPROVAL"
    )
    
    updated = _case_service.repository.update(
        case_id=case_id,
        updates={
            "extracted_custody_events": eir_data,
            "normalized_timeline": timeline,
            "assessment": assessment,
            "settlement_state": settlement_state.model_dump(mode="json"),
            "status": CaseStatus.ASSESSMENT_READY
        }
    )
    
    return updated


@router.post("/demo/load-failure", response_model=CaseModel)
def load_demo_failure_case() -> CaseModel:
    """
    Generates a failure demo case with corrupted/unreadable EIR scan and check digit failure.
    """
    case_id = "CASE-2026-FAIL-UNREAD"
    _case_service.repository.delete(case_id)
    
    shipment = ShipmentInfo(
        container_id="MSKU9999999",  # Invalid checksum
        commodity="Frozen Seafood",
        declared_value_usd=45000.0,
        claimed_loss_usd=45000.0,
        origin_facility="Port of Houston Terminal",
        destination_facility="Dallas Cold Storage",
        carrier_name="Gulf Drayage Inc."
    )
    
    case = _case_service.create_case(
        shipment_info=shipment,
        actor="DEMO_LOADER",
        initial_status=CaseStatus.FAILED,
        custom_case_id=case_id
    )
    
    eir_data = {
        "container_id": "MSKU9999999",
        "iso_check_digit_valid": False,
        "extraction_status": "FAILED",
        "damage_remarks": "UNREADABLE SCAN - ILLEGIBLE HANDWRITTEN STAMP",
        "validation_flags": [
            {"flag_name": "ISO_6346_CHECKSUM_FAILED", "description": "Check digit mismatch: calculated 2, found 9."},
            {"flag_name": "ILLEGIBLE_TIMESTAMP", "description": "Timestamp stamp blurred and unparseable."}
        ]
    }
    
    updated = _case_service.repository.update(
        case_id=case_id,
        updates={
            "extracted_custody_events": eir_data,
            "status": CaseStatus.FAILED
        }
    )
    return updated


@router.post("/demo/reset", response_model=Dict[str, Any])
def reset_demo_state() -> Dict[str, Any]:
    """
    Clears all cases in repository and returns clean state.
    """
    _case_service.repository.clear()
    return {"status": "success", "message": "Demo cases reset to clean state."}

