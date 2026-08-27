import uuid
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime, timezone, timedelta

from ..models.investigation import (
    CustodyWindow,
    CustodyRole,
    FusedTimelineEvent,
    TimelineEventType,
    DeterministicCustodyOverlap,
    CaseDisputeMetadata
)
from ..models.telemetry import IncidentTelemetry, TelemetryBreach
from ..models.documents import ExtractedEIRData, HandoverCondition
from .timestamp_normalizer import TimestampNormalizer
from ..observability.tracer import trace_span


class DeterministicTimelineFusionEngine:
    """
    Deterministic timeline and custody fusion engine.
    Fuses discrete EIR handovers with continuous IoT sensor time series to calculate
    Care, Custody, and Control (CCC) at the exact moment of earliest recorded breach.
    """

    @classmethod
    def fuse_timeline(
        cls,
        telemetry: IncidentTelemetry,
        extracted_eir: Optional[ExtractedEIRData],
        case_metadata: CaseDisputeMetadata,
        default_timezone: Optional[str] = None
    ) -> Tuple[List[FusedTimelineEvent], List[CustodyWindow], DeterministicCustodyOverlap]:
        """
        Fuses events and calculates deterministic custody overlap at earliest recorded breach.
        """
        case_id = getattr(case_metadata, "case_id", getattr(case_metadata, "shipment_id", "UNKNOWN"))
        with trace_span(
            name="Deterministic Custody & Breach Interval Matching",
            category="TIMELINE_FUSION",
            attributes={"case_id": case_id}
        ) as span:
            events: List[FusedTimelineEvent] = []
            windows: List[CustodyWindow] = []

            # 1. Parse Handover Timestamp from EIR if present
            handover_dt_utc: Optional[datetime] = None
            releasing_party = (
                (extracted_eir.releasing_entity if extracted_eir else None)
                or case_metadata.shipper_name
                or "Origin Consignor"
            )
            receiving_party = (
                (extracted_eir.receiving_entity if extracted_eir else None)
                or (extracted_eir.carrier_name if extracted_eir else None)
                or case_metadata.carrier_name
                or "Motor Carrier"
            )

            if extracted_eir and extracted_eir.raw_timestamp_str:
                dt, req_verify, _ = TimestampNormalizer.normalize(
                    extracted_eir.raw_timestamp_str,
                    default_timezone=default_timezone or extracted_eir.extracted_timezone_str
                )
                handover_dt_utc = dt

            # 2. Add EIR Handover & Document Exception Events to Timeline
            if handover_dt_utc:
                events.append(
                    FusedTimelineEvent(
                        event_id=f"EVT-EIR-{uuid.uuid4().hex[:6]}",
                        timestamp_utc=handover_dt_utc,
                        event_type=TimelineEventType.CUSTODY_HANDOVER,
                        title=f"Custody Handover: {releasing_party} -> {receiving_party}",
                        description=(
                            f"Equipment interchange verified. Releasing party: '{releasing_party}', "
                            f"Receiving party: '{receiving_party}'. Gate event: {extracted_eir.gate_event_type.value if extracted_eir else 'INGATE'}."
                        ),
                        location_name=(getattr(extracted_eir, "facility_location", None) or getattr(extracted_eir, "issuing_facility", None) or "Interchange Terminal"),
                        custody_holder=receiving_party,
                        custody_role=CustodyRole.DRAYAGE_ORIGIN,
                        evidence_source="EIR Document",
                        is_breach_event=False
                    )
                )
            if extracted_eir and extracted_eir.handwritten_notes:
                for note in extracted_eir.handwritten_notes:
                    events.append(
                        FusedTimelineEvent(
                            event_id=f"EVT-DOC-NOTE-{uuid.uuid4().hex[:6]}",
                            timestamp_utc=handover_dt_utc or datetime.now(timezone.utc),
                            event_type=TimelineEventType.DOCUMENT_EXCEPTION,
                            title="Handwritten Gate Annotation",
                            description=note,
                            custody_holder=receiving_party,
                            severity="INFO",
                            evidence_source="EIR Handwritten Remarks",
                            is_breach_event=False
                        )
                    )

        # 3. Add Telemetry Breach Events
        earliest_breach_dt: Optional[datetime] = None
        earliest_breach_obj: Optional[TelemetryBreach] = None

        for breach in telemetry.breaches:
            if earliest_breach_dt is None or breach.earliest_recorded_breach < earliest_breach_dt:
                earliest_breach_dt = breach.earliest_recorded_breach
                earliest_breach_obj = breach

            events.append(
                FusedTimelineEvent(
                    event_id=f"EVT-BRCH-{breach.breach_id}",
                    timestamp_utc=breach.breach_start,
                    event_type=TimelineEventType.TELEMETRY_BREACH_START,
                    title=f"Sensor Breach Start: {breach.breach_type.value}",
                    description=(
                        f"Continuous violation detected. Peak value: {breach.peak_value:.2f}, "
                        f"Threshold: {breach.threshold_value:.2f}, Duration: {breach.duration_seconds / 60:.1f} mins."
                    ),
                    custody_holder=None,  # Assigned after window resolution
                    severity="CRITICAL",
                    evidence_source="IoT Telemetry Sensor",
                    is_breach_event=True,
                    metadata={"breach_id": breach.breach_id, "peak_value": breach.peak_value}
                )
            )

        # 4. Construct Continuous Custody Windows
        sensor_start_dt = (
            telemetry.readings[0].timestamp_utc
            if telemetry.readings and telemetry.readings[0].timestamp_utc
            else telemetry.earliest_recorded_breach
        )
        sensor_end_dt = (
            telemetry.readings[-1].timestamp_utc
            if telemetry.readings and telemetry.readings[-1].timestamp_utc
            else telemetry.latest_recorded_breach
        )

        if handover_dt_utc:
            # Window 1: Origin / Releasing Custodian
            w1_start = sensor_start_dt if (sensor_start_dt and sensor_start_dt < handover_dt_utc) else (handover_dt_utc - timedelta(hours=12))
            w1 = CustodyWindow(
                window_id="WIN-001",
                holder_name=releasing_party,
                role=CustodyRole.SHIPPER,
                start_time_utc=w1_start,
                end_time_utc=handover_dt_utc,
                start_location=case_metadata.origin_facility or "Origin Facility",
                end_location=extracted_eir.facility_location if extracted_eir else "Interchange Terminal",
                eir_handover_status="PRE_HANDOVER",
                is_active_window=True
            )
            windows.append(w1)

            # Window 2: Receiving Carrier / Terminal
            w2_end = sensor_end_dt if (sensor_end_dt and sensor_end_dt > handover_dt_utc) else (handover_dt_utc + timedelta(hours=24))
            w2 = CustodyWindow(
                window_id="WIN-002",
                holder_name=receiving_party,
                role=CustodyRole.DRAYAGE_ORIGIN if "drayage" in receiving_party.lower() else CustodyRole.OCEAN_CARRIER,
                start_time_utc=handover_dt_utc,
                end_time_utc=w2_end,
                start_location=extracted_eir.facility_location if extracted_eir else "Interchange Terminal",
                end_location=case_metadata.destination_facility or "Destination Port",
                eir_handover_status=extracted_eir.condition_summary.value if extracted_eir else "CLEAN",
                is_active_window=True
            )
            windows.append(w2)
        elif sensor_start_dt and sensor_end_dt:
            # Single fallback window when handover timestamp is missing
            default_holder = receiving_party or releasing_party
            windows.append(
                CustodyWindow(
                    window_id="WIN-001",
                    holder_name=default_holder,
                    role=CustodyRole.UNKNOWN,
                    start_time_utc=sensor_start_dt,
                    end_time_utc=sensor_end_dt,
                    is_active_window=True
                )
            )

        # 5. Deterministically Calculate Overlap at Earliest Breach
        overlap = cls._calculate_overlap(
            windows=windows,
            earliest_breach_dt=earliest_breach_dt,
            earliest_breach_obj=earliest_breach_obj,
            handover_dt_utc=handover_dt_utc,
            releasing_party=releasing_party,
            receiving_party=receiving_party
        )

        # Assign resolved custody holder to breach timeline events
        for ev in events:
            if ev.custody_holder is None and ev.timestamp_utc:
                ev_holder, ev_role = cls._resolve_custody_at_instant(windows, ev.timestamp_utc)
                ev.custody_holder = ev_holder
                ev.custody_role = ev_role

        # Sort timeline events chronologically
        events.sort(key=lambda e: e.timestamp_utc)

        return events, windows, overlap

    @classmethod
    def _resolve_custody_at_instant(
        cls,
        windows: List[CustodyWindow],
        dt: datetime
    ) -> Tuple[Optional[str], CustodyRole]:
        """Finds the custody window containing the specified timestamp."""
        for win in windows:
            if win.start_time_utc <= dt:
                if win.end_time_utc is None or dt <= win.end_time_utc:
                    return win.holder_name, win.role
        if windows:
            # If prior to first window, return first window holder
            if dt < windows[0].start_time_utc:
                return windows[0].holder_name, windows[0].role
            # If after last window, return last window holder
            return windows[-1].holder_name, windows[-1].role
        return None, CustodyRole.UNKNOWN

    @classmethod
    def _calculate_overlap(
        cls,
        windows: List[CustodyWindow],
        earliest_breach_dt: Optional[datetime],
        earliest_breach_obj: Optional[TelemetryBreach],
        handover_dt_utc: Optional[datetime],
        releasing_party: str,
        receiving_party: str
    ) -> DeterministicCustodyOverlap:
        """
        Pure deterministic calculation of custody holder at the moment of earliest sensor breach.
        """
        if earliest_breach_dt is None or earliest_breach_obj is None:
            return DeterministicCustodyOverlap(
                has_breach=False,
                culpable_party=None,
                culpable_role=CustodyRole.UNKNOWN,
                earliest_breach_timestamp_utc=None,
                overlap_confidence=1.0,
                basis_reasoning="No sensor threshold breaches (temperature excursions or high-G shock impacts) were detected in telemetry."
            )

        if handover_dt_utc is None:
            # Cannot determine with 100% confidence without EIR handover timestamp
            holder_name = windows[0].holder_name if windows else "Unassigned Custodian"
            return DeterministicCustodyOverlap(
                has_breach=True,
                culpable_party=holder_name,
                culpable_role=CustodyRole.UNKNOWN,
                earliest_breach_timestamp_utc=earliest_breach_dt,
                custody_window_id=windows[0].window_id if windows else None,
                overlap_confidence=0.45,
                basis_reasoning=(
                    f"Earliest sensor breach occurred at {earliest_breach_dt.isoformat()} UTC, "
                    f"but EIR handover timestamp was missing or unparseable. Custody window cannot be definitively partitioned."
                )
            )

        # Helper to dynamically calculate confidence based on temporal distance from custody boundary
        def _calc_boundary_confidence(delta: float) -> float:
            if delta >= 60.0:
                return 0.98
            elif delta >= 30.0:
                return round(0.90 + (delta - 30.0) / 30.0 * 0.08, 2)
            elif delta >= 10.0:
                return round(0.82 + (delta - 10.0) / 20.0 * 0.08, 2)
            else:
                return round(0.75 + max(0.0, delta) / 10.0 * 0.07, 2)

        # Compare earliest breach to EIR handover timestamp
        if earliest_breach_dt < handover_dt_utc:
            delta_mins = (handover_dt_utc - earliest_breach_dt).total_seconds() / 60.0
            calculated_conf = _calc_boundary_confidence(delta_mins)
            win1 = next((w for w in windows if w.window_id == "WIN-001"), None)
            return DeterministicCustodyOverlap(
                has_breach=True,
                culpable_party=releasing_party,
                culpable_role=CustodyRole.SHIPPER,
                earliest_breach_timestamp_utc=earliest_breach_dt,
                custody_window_id=win1.window_id if win1 else "WIN-001",
                custody_window_start_utc=win1.start_time_utc if win1 else None,
                custody_window_end_utc=handover_dt_utc,
                overlap_confidence=calculated_conf,
                basis_reasoning=(
                    f"Earliest recorded {earliest_breach_obj.breach_type.value} occurred at {earliest_breach_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}, "
                    f"which is {delta_mins:.1f} minutes BEFORE carrier custody handover at {handover_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                    f"Deterministic Care, Custody, and Control (CCC) resided with releasing party '{releasing_party}' at inception of loss."
                )
            )
        else:
            delta_mins = (earliest_breach_dt - handover_dt_utc).total_seconds() / 60.0
            calculated_conf = _calc_boundary_confidence(delta_mins)
            win2 = next((w for w in windows if w.window_id == "WIN-002"), None)
            return DeterministicCustodyOverlap(
                has_breach=True,
                culpable_party=receiving_party,
                culpable_role=CustodyRole.DRAYAGE_ORIGIN if "drayage" in receiving_party.lower() else CustodyRole.OCEAN_CARRIER,
                earliest_breach_timestamp_utc=earliest_breach_dt,
                custody_window_id=win2.window_id if win2 else "WIN-002",
                custody_window_start_utc=handover_dt_utc,
                custody_window_end_utc=win2.end_time_utc if win2 else None,
                overlap_confidence=calculated_conf,
                basis_reasoning=(
                    f"Earliest recorded {earliest_breach_obj.breach_type.value} occurred at {earliest_breach_dt.strftime('%Y-%m-%d %H:%M:%S UTC')}, "
                    f"which is {delta_mins:.1f} minutes AFTER carrier custody handover at {handover_dt_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}. "
                    f"Deterministic Care, Custody, and Control (CCC) had transferred to receiving carrier '{receiving_party}' prior to inception of loss."
                )
            )
