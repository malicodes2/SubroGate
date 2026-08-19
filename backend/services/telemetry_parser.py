import csv
import io
import re
from typing import List, Dict, Any, Tuple, Optional
from .timestamp_normalizer import TimestampNormalizer
from ..models.telemetry import NormalizedTelemetryReading, DataQualityReport

# Standard field alias mappings
COLUMN_ALIASES: Dict[str, List[str]] = {
    "timestamp": [
        "timestamp", "datetime", "date_time", "time", "ts", "recorded_at", 
        "log_time", "sample_time", "event_time", "timestamp_utc", "date", "utc_time"
    ],
    "temperature": [
        "temperature", "temp", "temp_c", "temperature_c", "reefer_temp", 
        "cargo_temp", "ambient_temp", "temperature_celsius", "internal_temp"
    ],
    "temperature_f": [
        "temp_f", "temperature_f", "reefer_temp_f", "temp_fahrenheit"
    ],
    "humidity": [
        "humidity", "rh", "humidity_pct", "relative_humidity", "rel_humidity", "humidity_%"
    ],
    "shock": [
        "shock", "shock_g", "g_force", "acceleration", "peak_g", 
        "vibration_g", "impact_g", "accel_g", "shock_peak"
    ],
    "latitude": [
        "latitude", "lat", "gps_lat", "gps_latitude", "y", "geo_lat"
    ],
    "longitude": [
        "longitude", "lon", "lng", "gps_lon", "gps_lng", "gps_longitude", "x", "geo_lon", "geo_lng"
    ],
    "container_id": [
        "container_id", "container", "container_no", "container_number", "cntr_no", 
        "unit_id", "trailer_id", "box_id", "asset_id"
    ],
    "device_id": [
        "device_id", "device", "logger_id", "sensor_id", "tracker_id", 
        "serial_number", "serial_no", "imei", "beacon_id"
    ]
}

class TelemetryParser:
    """
    Deterministic CSV telemetry parser and column normalizer.
    Tolerates column naming variations without heuristic LLM dependence.
    """

    @classmethod
    def resolve_columns(cls, header: List[str]) -> Dict[str, str]:
        """
        Maps normalized field names to actual CSV header names.
        """
        mapping: Dict[str, str] = {}
        clean_header = [h.strip().lower().replace(" ", "_").replace("-", "_") for h in header]

        for canonical_name, aliases in COLUMN_ALIASES.items():
            for i, raw_col in enumerate(clean_header):
                if raw_col in aliases:
                    mapping[canonical_name] = header[i]
                    break
        return mapping

    @classmethod
    def parse_csv_content(
        cls,
        csv_text: str,
        default_timezone: Optional[str] = None
    ) -> Tuple[List[NormalizedTelemetryReading], DataQualityReport]:
        """
        Parses CSV string into normalized readings and data quality report.
        """
        readings: List[NormalizedTelemetryReading] = []
        report = DataQualityReport()

        if not csv_text or not csv_text.strip():
            report.quality_flags.append("EMPTY_CSV_INPUT")
            report.issues.append({"type": "EMPTY_INPUT", "message": "Provided CSV content is empty"})
            return readings, report

        # Read CSV rows using standard library
        try:
            reader = csv.reader(io.StringIO(csv_text.strip()))
            rows = list(reader)
        except Exception as e:
            report.quality_flags.append("CSV_SYNTAX_ERROR")
            report.issues.append({"type": "SYNTAX_ERROR", "message": f"Malformed CSV structure: {str(e)}"})
            return readings, report

        if not rows:
            report.quality_flags.append("EMPTY_CSV_INPUT")
            return readings, report

        header = rows[0]
        col_map = cls.resolve_columns(header)
        report.total_rows_parsed = len(rows) - 1

        # Check required columns
        if "timestamp" not in col_map:
            report.quality_flags.append("MISSING_TIMESTAMP_COLUMN")
            report.issues.append({
                "type": "MISSING_REQUIRED_COLUMN",
                "message": f"CSV must contain a timestamp column. Detected headers: {header}"
            })
            return readings, report

        header_indices = {h.strip(): idx for idx, h in enumerate(header)}

        def get_val(row: List[str], canonical: str) -> Optional[str]:
            col_name = col_map.get(canonical)
            if not col_name or col_name not in header_indices:
                return None
            idx = header_indices[col_name]
            if idx < len(row):
                val = row[idx].strip()
                return val if val != "" else None
            return None

        # Parse data rows
        for row_idx, row in enumerate(rows[1:], start=2):
            if not row or all(c.strip() == "" for c in row):
                continue # Skip pure empty line

            raw_row_dict = {header[i]: row[i] if i < len(row) else "" for i in range(len(header))}
            validation_notes: List[str] = []

            # 1. Parse Timestamp
            raw_ts = get_val(row, "timestamp")
            if not raw_ts:
                report.malformed_rows_count += 1
                report.issues.append({
                    "row_index": row_idx,
                    "type": "MISSING_TIMESTAMP_VALUE",
                    "message": "Row has missing or empty timestamp"
                })
                readings.append(
                    NormalizedTelemetryReading(
                        row_index=row_idx,
                        raw_timestamp_str="",
                        requires_human_verification=True,
                        verification_reason="Missing timestamp value in row",
                        is_valid=False,
                        validation_notes=["Missing timestamp value"],
                        raw_row=raw_row_dict
                    )
                )
                continue

            dt_utc, req_human, verify_reason = TimestampNormalizer.normalize(raw_ts, default_timezone)
            if req_human:
                report.ambiguous_timezones_count += 1
                validation_notes.append(verify_reason or "Timezone ambiguous")

            # 2. Parse Temperature (Celsius or Fahrenheit conversion)
            temp_c: Optional[float] = None
            raw_temp_c = get_val(row, "temperature")
            raw_temp_f = get_val(row, "temperature_f")

            if raw_temp_c is not None:
                try:
                    temp_c = float(raw_temp_c)
                except ValueError:
                    validation_notes.append(f"Invalid non-numeric temperature value: '{raw_temp_c}'")
                    report.issues.append({"row_index": row_idx, "type": "INVALID_NUMERIC", "field": "temperature", "value": raw_temp_c})
            elif raw_temp_f is not None:
                try:
                    temp_f = float(raw_temp_f)
                    temp_c = round((temp_f - 32.0) * (5.0 / 9.0), 2)
                    validation_notes.append(f"Converted from {temp_f}°F to {temp_c}°C")
                except ValueError:
                    validation_notes.append(f"Invalid non-numeric temperature_f value: '{raw_temp_f}'")

            # 3. Parse Shock
            shock_g: Optional[float] = None
            raw_shock = get_val(row, "shock")
            if raw_shock is not None:
                try:
                    shock_g = float(raw_shock)
                except ValueError:
                    validation_notes.append(f"Invalid non-numeric shock value: '{raw_shock}'")

            # 4. Parse Humidity
            humidity: Optional[float] = None
            raw_hum = get_val(row, "humidity")
            if raw_hum is not None:
                try:
                    hum_val = float(raw_hum)
                    if 0 <= hum_val <= 100:
                        humidity = hum_val
                    else:
                        validation_notes.append(f"Humidity out of percentage range [0, 100]: {hum_val}")
                except ValueError:
                    validation_notes.append(f"Invalid non-numeric humidity value: '{raw_hum}'")

            # 5. Parse Coordinates
            lat: Optional[float] = None
            lon: Optional[float] = None
            raw_lat = get_val(row, "latitude")
            raw_lon = get_val(row, "longitude")

            if raw_lat is not None and raw_lon is not None:
                try:
                    lat_f = float(raw_lat)
                    lon_f = float(raw_lon)
                    if -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0:
                        lat = lat_f
                        lon = lon_f
                    else:
                        report.impossible_coordinates_count += 1
                        validation_notes.append(f"Impossible GPS coordinates: ({lat_f}, {lon_f})")
                        report.issues.append({"row_index": row_idx, "type": "IMPOSSIBLE_COORDINATES", "lat": lat_f, "lon": lon_f})
                except ValueError:
                    validation_notes.append(f"Invalid GPS numeric strings: lat='{raw_lat}', lon='{raw_lon}'")

            # 6. Metadata (Container, Device)
            container_id = get_val(row, "container_id")
            device_id = get_val(row, "device_id")

            is_record_valid = (dt_utc is not None)
            if is_record_valid:
                report.valid_readings_count += 1
            else:
                report.malformed_rows_count += 1

            readings.append(
                NormalizedTelemetryReading(
                    row_index=row_idx,
                    timestamp_utc=dt_utc,
                    raw_timestamp_str=raw_ts,
                    requires_human_verification=req_human,
                    verification_reason=verify_reason,
                    temperature_c=temp_c,
                    humidity_pct=humidity,
                    shock_g=shock_g,
                    latitude=lat,
                    longitude=lon,
                    container_id=container_id,
                    device_id=device_id,
                    is_valid=is_record_valid,
                    validation_notes=validation_notes,
                    raw_row=raw_row_dict
                )
            )

        return readings, report
