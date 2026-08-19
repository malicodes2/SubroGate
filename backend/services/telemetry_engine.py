from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from statistics import median
from .telemetry_parser import TelemetryParser
from ..models.telemetry import (
    NormalizedTelemetryReading,
    TelemetryBreach,
    BreachType,
    DataQualityReport,
    TelemetryThresholdConfig,
    IncidentTelemetry
)
from ..observability.tracer import trace_span

class DeterministicTelemetryEngine:
    """
    Pure algorithmic telemetry normalization and breach detection engine.
    Zero LLM dependencies.
    """

    @classmethod
    def process_csv(
        cls,
        csv_text: str,
        thresholds: Optional[TelemetryThresholdConfig] = None,
        default_timezone: Optional[str] = None
    ) -> IncidentTelemetry:
        """
        End-to-end deterministic processing of raw CSV telemetry:
        1. Normalization & Parsing
        2. Temporal & Data Quality Validation
        3. Threshold Breach Interval Detection
        4. Incident Construction
        """
        with trace_span(
            name="IoT Telemetry Normalization & Breach Detection",
            category="TELEMETRY",
            attributes={"telemetry.raw_length": len(csv_text)}
        ) as span:
            cfg = thresholds or TelemetryThresholdConfig()
            raw_readings, report = TelemetryParser.parse_csv_content(csv_text, default_timezone)

            # Filter valid chronological readings for analysis
            valid_readings = [r for r in raw_readings if r.is_valid and r.timestamp_utc is not None]
            # Sort chronologically by UTC timestamp
            valid_readings.sort(key=lambda r: r.timestamp_utc)

            # Extract top-level container/device IDs from readings if present
            container_id = next((r.container_id for r in valid_readings if r.container_id), None)
            device_id = next((r.device_id for r in valid_readings if r.device_id), None)

            span.set_attribute("telemetry.valid_samples", len(valid_readings))
            span.set_attribute("device_id", device_id or "UNKNOWN")
            if container_id:
                span.set_attribute("container_id", container_id)

            # 2. Data Quality Analysis
            cls._audit_temporal_quality(valid_readings, report, cfg)

            # 3. Deterministic Breach Detection
            breaches = cls._detect_all_breaches(valid_readings, cfg)

            # 4. Global earliest and latest breach calculations
            has_breach = len(breaches) > 0
            earliest_breach = min((b.earliest_recorded_breach for b in breaches), default=None)
            latest_breach = max((b.breach_end for b in breaches), default=None)

            span.set_attribute("telemetry.has_breach", has_breach)
            span.set_attribute("telemetry.breach_count", len(breaches))

            # 5. Compute sampling resolution
            sampling_res = cls._compute_sampling_resolution(valid_readings)

            # 6. Precision Statement
            if sampling_res is not None and sampling_res > 0:
                res_mins = sampling_res / 60.0
                precision_statement = (
                    f"Discrete sampling interval: {sampling_res:.0f}s ({res_mins:.1f} min). "
                    f"Event timestamps represent discrete sensor observation logs bounded by ±{sampling_res:.0f}s. "
                    "Do not infer sub-interval or millisecond-level precision."
                )
            else:
                precision_statement = "Sparse or irregular telemetry timestamps. Precise continuous duration cannot be guaranteed."

            return IncidentTelemetry(
                container_id=container_id,
                device_id=device_id,
                has_breach=has_breach,
                breaches=breaches,
                data_quality=report,
                readings=valid_readings,
                earliest_recorded_breach=earliest_breach,
                latest_recorded_breach=latest_breach,
                sampling_resolution_seconds=sampling_res,
                precision_statement=precision_statement
            )

    @classmethod
    def _audit_temporal_quality(
        cls,
        readings: List[NormalizedTelemetryReading],
        report: DataQualityReport,
        cfg: TelemetryThresholdConfig
    ) -> None:
        if len(readings) < 2:
            return

        seen_timestamps = set()
        intervals: List[float] = []

        for i, r in enumerate(readings):
            ts = r.timestamp_utc
            if ts in seen_timestamps:
                report.duplicate_timestamps_count += 1
                report.issues.append({
                    "type": "DUPLICATE_TIMESTAMP",
                    "row_index": r.row_index,
                    "timestamp": ts.isoformat()
                })
                r.validation_notes.append("Duplicate timestamp detected")
            else:
                seen_timestamps.add(ts)

            if i > 0:
                prev_ts = readings[i - 1].timestamp_utc
                delta_sec = (ts - prev_ts).total_seconds()
                if delta_sec > 0:
                    intervals.append(delta_sec)

                # Check for significant missing interval gap
                max_gap = cfg.max_gap_tolerance_seconds or 3600.0
                if delta_sec > max_gap:
                    report.missing_intervals_count += 1
                    gap_mins = delta_sec / 60.0
                    report.issues.append({
                        "type": "TELEMETRY_GAP",
                        "start": prev_ts.isoformat(),
                        "end": ts.isoformat(),
                        "gap_duration_seconds": delta_sec,
                        "message": f"Telemetry gap of {gap_mins:.1f} minutes between {prev_ts} and {ts}"
                    })

        if report.duplicate_timestamps_count > 0:
            report.quality_flags.append("DUPLICATE_TIMESTAMPS_PRESENT")
        if report.missing_intervals_count > 0:
            report.quality_flags.append("TELEMETRY_GAPS_DETECTED")
        if report.ambiguous_timezones_count > 0:
            report.quality_flags.append("AMBIGUOUS_TIMEZONES_FLAGGED")
        if report.impossible_coordinates_count > 0:
            report.quality_flags.append("IMPOSSIBLE_COORDINATES_DETECTED")

    @classmethod
    def _compute_sampling_resolution(cls, readings: List[NormalizedTelemetryReading]) -> Optional[float]:
        if len(readings) < 2:
            return None
        deltas = [
            (readings[i].timestamp_utc - readings[i - 1].timestamp_utc).total_seconds()
            for i in range(1, len(readings))
            if (readings[i].timestamp_utc - readings[i - 1].timestamp_utc).total_seconds() > 0
        ]
        if not deltas:
            return None
        return round(float(median(deltas)), 1)

    @classmethod
    def _detect_all_breaches(
        cls,
        readings: List[NormalizedTelemetryReading],
        cfg: TelemetryThresholdConfig
    ) -> List[TelemetryBreach]:
        breaches: List[TelemetryBreach] = []

        # 1. Temperature High Breach (Excursion above max setpoint)
        if cfg.temp_max_c is not None:
            high_temp_breaches = cls._detect_continuous_breaches(
                readings=readings,
                val_getter=lambda r: r.temperature_c,
                is_violating=lambda v: v > cfg.temp_max_c,
                threshold_val=cfg.temp_max_c,
                breach_type=BreachType.TEMPERATURE_HIGH,
                tolerance_sec=cfg.temp_duration_tolerance_seconds
            )
            breaches.extend(high_temp_breaches)

        # 2. Temperature Low Breach (Excursion below min setpoint)
        if cfg.temp_min_c is not None:
            low_temp_breaches = cls._detect_continuous_breaches(
                readings=readings,
                val_getter=lambda r: r.temperature_c,
                is_violating=lambda v: v < cfg.temp_min_c,
                threshold_val=cfg.temp_min_c,
                breach_type=BreachType.TEMPERATURE_LOW,
                tolerance_sec=cfg.temp_duration_tolerance_seconds
            )
            breaches.extend(low_temp_breaches)

        # 3. Shock G-Force Breach (Instantaneous / Point spikes)
        if cfg.shock_g_threshold is not None:
            shock_breaches = cls._detect_point_breaches(
                readings=readings,
                val_getter=lambda r: r.shock_g,
                is_violating=lambda v: v >= cfg.shock_g_threshold,
                threshold_val=cfg.shock_g_threshold,
                breach_type=BreachType.SHOCK_EXCESS
            )
            breaches.extend(shock_breaches)

        # Sort all breaches chronologically
        breaches.sort(key=lambda b: b.breach_start)
        return breaches

    @classmethod
    def _detect_continuous_breaches(
        cls,
        readings: List[NormalizedTelemetryReading],
        val_getter: Any,
        is_violating: Any,
        threshold_val: float,
        breach_type: BreachType,
        tolerance_sec: float = 0.0
    ) -> List[TelemetryBreach]:
        breaches: List[TelemetryBreach] = []
        current_streak: List[NormalizedTelemetryReading] = []

        def flush_streak():
            if not current_streak:
                return
            start_t = current_streak[0].timestamp_utc
            end_t = current_streak[-1].timestamp_utc
            duration = (end_t - start_t).total_seconds()

            if duration >= tolerance_sec or len(current_streak) >= 1:
                vals = [val_getter(r) for r in current_streak if val_getter(r) is not None]
                peak = max(vals) if breach_type == BreachType.TEMPERATURE_HIGH else min(vals)
                
                breaches.append(
                    TelemetryBreach(
                        breach_id=f"BREACH-{breach_type.value[:4]}-{len(breaches) + 1:02d}",
                        breach_type=breach_type,
                        earliest_recorded_breach=start_t,
                        breach_start=start_t,
                        breach_end=end_t,
                        peak_value=round(peak, 2),
                        threshold_value=threshold_val,
                        duration_seconds=duration,
                        affected_readings_count=len(current_streak),
                        affected_records_sample=current_streak[:10],
                        precision_note=f"Continuous threshold violation interval encompassing {len(current_streak)} discrete readings."
                    )
                )

        for r in readings:
            val = val_getter(r)
            if val is not None and is_violating(val):
                current_streak.append(r)
            else:
                if current_streak:
                    flush_streak()
                    current_streak = []

        if current_streak:
            flush_streak()

        return breaches

    @classmethod
    def _detect_point_breaches(
        cls,
        readings: List[NormalizedTelemetryReading],
        val_getter: Any,
        is_violating: Any,
        threshold_val: float,
        breach_type: BreachType
    ) -> List[TelemetryBreach]:
        breaches: List[TelemetryBreach] = []

        for r in readings:
            val = val_getter(r)
            if val is not None and is_violating(val):
                breaches.append(
                    TelemetryBreach(
                        breach_id=f"BREACH-{breach_type.value[:4]}-{len(breaches) + 1:02d}",
                        breach_type=breach_type,
                        earliest_recorded_breach=r.timestamp_utc,
                        breach_start=r.timestamp_utc,
                        breach_end=r.timestamp_utc,
                        peak_value=round(val, 2),
                        threshold_value=threshold_val,
                        duration_seconds=0.0,
                        affected_readings_count=1,
                        affected_records_sample=[r],
                        precision_note="Instantaneous threshold breach recorded on single sensor reading."
                    )
                )

        return breaches
