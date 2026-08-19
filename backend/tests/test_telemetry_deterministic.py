import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from backend.main import create_app
from backend.services.timestamp_normalizer import TimestampNormalizer
from backend.services.telemetry_parser import TelemetryParser
from backend.services.telemetry_engine import DeterministicTelemetryEngine
from backend.models.telemetry import (
    TelemetryThresholdConfig,
    BreachType,
    IncidentTelemetry
)

@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)

# ==============================================================================
# 1. TIMESTAMP NORMALIZATION TESTS
# ==============================================================================

def test_utc_timestamp_normalization():
    dt, req_human, reason = TimestampNormalizer.normalize("2026-06-15T14:30:00Z")
    assert dt is not None
    assert dt == datetime(2026, 6, 15, 14, 30, 0, tzinfo=timezone.utc)
    assert req_human is False
    assert reason is None

def test_positive_timezone_offset():
    # +05:30 (India Standard Time) -> 14:30 IST is 09:00 UTC
    dt, req_human, reason = TimestampNormalizer.normalize("2026-06-15T14:30:00+05:30")
    assert dt is not None
    assert dt == datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
    assert req_human is False

def test_negative_timezone_offset():
    # -07:00 (PDT) -> 14:30 PDT is 21:30 UTC
    dt, req_human, reason = TimestampNormalizer.normalize("2026-06-15T14:30:00-07:00")
    assert dt is not None
    assert dt == datetime(2026, 6, 15, 21, 30, 0, tzinfo=timezone.utc)
    assert req_human is False

def test_dst_transition_handling():
    # Winter EST (-05:00) vs Summer EDT (-04:00)
    dt_est, req_est, _ = TimestampNormalizer.normalize("2026-01-15 12:00:00 EST")
    assert dt_est == datetime(2026, 1, 15, 17, 0, 0, tzinfo=timezone.utc)
    assert req_est is False

    dt_edt, req_edt, _ = TimestampNormalizer.normalize("2026-07-15 12:00:00 EDT")
    assert dt_edt == datetime(2026, 7, 15, 16, 0, 0, tzinfo=timezone.utc)
    assert req_edt is False

def test_missing_timezone_flags_human_verification():
    # Missing explicit timezone token
    dt, req_human, reason = TimestampNormalizer.normalize("2026-06-15 14:30:00")
    assert dt is not None
    assert req_human is True
    assert "Missing explicit timezone" in reason

def test_malformed_timestamp_handling():
    dt, req_human, reason = TimestampNormalizer.normalize("2026-99-99 45:99:00")
    assert dt is None
    assert req_human is True
    assert "Malformed timestamp" in reason

# ==============================================================================
# 2. CSV PARSING & DATA QUALITY TESTS
# ==============================================================================

def test_parse_csv_with_column_variations():
    csv_data = """sample_time,temp_f,vibration_g,lat,lng,cntr_no,tracker_id
2026-06-15T10:00:00Z,14.0,0.2,34.05,-118.25,MSKU-123456,DEV-99
2026-06-15T10:30:00Z,23.0,0.5,34.06,-118.26,MSKU-123456,DEV-99
"""
    readings, report = TelemetryParser.parse_csv_content(csv_data)
    assert len(readings) == 2
    assert report.valid_readings_count == 2
    assert readings[0].container_id == "MSKU-123456"
    assert readings[0].device_id == "DEV-99"
    # 14°F = -10°C
    assert readings[0].temperature_c == -10.0
    assert readings[0].shock_g == 0.2
    assert readings[0].latitude == 34.05

def test_detect_impossible_coordinates():
    csv_data = """timestamp,temperature,latitude,longitude
2026-06-15T10:00:00Z,-20.0,125.40,-118.25
2026-06-15T10:30:00Z,-20.0,34.05,-210.50
"""
    readings, report = TelemetryParser.parse_csv_content(csv_data)
    assert report.impossible_coordinates_count == 2
    assert readings[0].latitude is None # Reset on invalid coordinate

def test_detect_missing_values_and_malformed_rows():
    csv_data = """timestamp,temperature,shock_g
2026-06-15T10:00:00Z,-20.0,0.1
,invalid_temp,0.2
2026-06-15T11:00:00Z,NaN,0.3
"""
    readings, report = TelemetryParser.parse_csv_content(csv_data)
    assert len(readings) == 3
    assert report.valid_readings_count == 2
    assert report.malformed_rows_count == 1 # Row with empty timestamp

# ==============================================================================
# 3. BREACH DETECTION & INCIDENT RECONSTRUCTION TESTS
# ==============================================================================

def test_single_continuous_temperature_breach():
    # Frozen salmon setpoint max: -18.0°C. Excursion from 11:00 to 12:00 peaking at -8.0°C
    csv_data = """timestamp,temperature_c,shock_g,latitude,longitude,container_id
2026-06-15T10:00:00Z,-22.0,0.1,33.74,-118.25,MSKU-998811
2026-06-15T10:30:00Z,-21.5,0.2,33.74,-118.25,MSKU-998811
2026-06-15T11:00:00Z,-14.0,0.1,33.74,-118.25,MSKU-998811
2026-06-15T11:30:00Z,-8.0,0.1,33.74,-118.25,MSKU-998811
2026-06-15T12:00:00Z,-12.0,0.2,33.74,-118.25,MSKU-998811
2026-06-15T12:30:00Z,-20.0,0.1,33.74,-118.25,MSKU-998811
"""
    cfg = TelemetryThresholdConfig(temp_max_c=-18.0)
    incident = DeterministicTelemetryEngine.process_csv(csv_data, thresholds=cfg)

    assert incident.has_breach is True
    assert len(incident.breaches) == 1
    breach = incident.breaches[0]
    assert breach.breach_type == BreachType.TEMPERATURE_HIGH
    assert breach.breach_start == datetime(2026, 6, 15, 11, 0, 0, tzinfo=timezone.utc)
    assert breach.breach_end == datetime(2026, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    assert breach.peak_value == -8.0
    assert breach.duration_seconds == 3600.0
    assert breach.affected_readings_count == 3
    assert incident.container_id == "MSKU-998811"

def test_multiple_disjoint_breaches():
    # 2 separate temperature spikes + 1 high-G shock event
    csv_data = """timestamp,temperature_c,shock_g
2026-06-15T08:00:00Z,-22.0,0.1
2026-06-15T08:30:00Z,-10.0,0.2
2026-06-15T09:00:00Z,-22.0,0.1
2026-06-15T09:30:00Z,-22.0,5.4
2026-06-15T10:00:00Z,-22.0,0.1
2026-06-15T10:30:00Z,-5.0,0.1
2026-06-15T11:00:00Z,-7.0,0.1
2026-06-15T11:30:00Z,-22.0,0.1
"""
    cfg = TelemetryThresholdConfig(temp_max_c=-18.0, shock_g_threshold=4.0)
    incident = DeterministicTelemetryEngine.process_csv(csv_data, thresholds=cfg)

    assert incident.has_breach is True
    assert len(incident.breaches) == 3 # 2 temp breaches + 1 shock breach
    breach_types = [b.breach_type for b in incident.breaches]
    assert breach_types.count(BreachType.TEMPERATURE_HIGH) == 2
    assert breach_types.count(BreachType.SHOCK_EXCESS) == 1

def test_no_breach_scenario():
    csv_data = """timestamp,temperature_c,shock_g
2026-06-15T08:00:00Z,-22.0,0.2
2026-06-15T08:30:00Z,-21.0,0.3
2026-06-15T09:00:00Z,-22.5,0.1
"""
    cfg = TelemetryThresholdConfig(temp_max_c=-18.0, shock_g_threshold=4.0)
    incident = DeterministicTelemetryEngine.process_csv(csv_data, thresholds=cfg)

    assert incident.has_breach is False
    assert len(incident.breaches) == 0
    assert incident.earliest_recorded_breach is None

def test_duplicate_timestamps_and_gap_detection():
    csv_data = """timestamp,temperature_c
2026-06-15T08:00:00Z,-22.0
2026-06-15T08:00:00Z,-22.0
2026-06-15T12:00:00Z,-22.0
"""
    cfg = TelemetryThresholdConfig(max_gap_tolerance_seconds=3600.0)
    incident = DeterministicTelemetryEngine.process_csv(csv_data, thresholds=cfg)

    assert incident.data_quality.duplicate_timestamps_count == 1
    assert incident.data_quality.missing_intervals_count == 1
    assert "DUPLICATE_TIMESTAMPS_PRESENT" in incident.data_quality.quality_flags
    assert "TELEMETRY_GAPS_DETECTED" in incident.data_quality.quality_flags

# ==============================================================================
# 4. FASTAPI ENDPOINT INTEGRATION TESTS
# ==============================================================================

def test_api_process_telemetry_csv(client):
    csv_text = """timestamp,temperature_c,shock_g
2026-06-15T10:00:00Z,-22.0,0.1
2026-06-15T10:30:00Z,-10.0,0.2
"""
    response = client.post(
        "/api/telemetry/process-csv",
        json={
            "csv_content": csv_text,
            "thresholds": {"temp_max_c": -18.0}
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["has_breach"] is True
    assert len(data["breaches"]) == 1
    assert data["breaches"][0]["peak_value"] == -10.0

def test_api_validate_quality_endpoint(client):
    csv_text = """timestamp,latitude,longitude
2026-06-15T10:00:00Z,130.0,0.0
"""
    response = client.post(
        "/api/telemetry/validate-quality",
        json={"csv_content": csv_text}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["impossible_coordinates_count"] == 1
