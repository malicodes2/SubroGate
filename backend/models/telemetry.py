from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class BreachType(str, Enum):
    TEMPERATURE_HIGH = "TEMPERATURE_EXCURSION_HIGH"
    TEMPERATURE_LOW = "TEMPERATURE_EXCURSION_LOW"
    SHOCK_EXCESS = "IMPACT_SHOCK_EXCESS"
    HUMIDITY_HIGH = "HUMIDITY_EXCURSION_HIGH"

class NormalizedTelemetryReading(BaseModel):
    """Normalized single sensor data point in UTC."""
    row_index: int = Field(..., description="1-indexed row number from source CSV")
    timestamp_utc: Optional[datetime] = Field(None, description="UTC normalized timestamp")
    raw_timestamp_str: str = Field(..., description="Original raw timestamp string from CSV")
    requires_human_verification: bool = Field(default=False, description="True if timezone or data is ambiguous")
    verification_reason: Optional[str] = Field(None, description="Reason human verification is required")
    temperature_c: Optional[float] = Field(None, description="Temperature in Celsius")
    humidity_pct: Optional[float] = Field(None, description="Relative humidity percentage (0-100)")
    shock_g: Optional[float] = Field(None, description="Peak acceleration / shock in G-forces")
    latitude: Optional[float] = Field(None, description="GPS latitude (-90 to 90)")
    longitude: Optional[float] = Field(None, description="GPS longitude (-180 to 180)")
    container_id: Optional[str] = Field(None, description="Container or trailer identifier")
    device_id: Optional[str] = Field(None, description="Sensor logger device identifier")
    is_valid: bool = Field(default=True, description="True if record passed syntax and range checks")
    validation_notes: List[str] = Field(default_factory=list, description="Any data quality observations")
    raw_row: Dict[str, Any] = Field(default_factory=dict, description="Original unparsed CSV row")

class TelemetryBreach(BaseModel):
    """Deterministic sensor threshold breach interval."""
    breach_id: str = Field(..., description="Unique identifier for the breach event")
    breach_type: BreachType = Field(..., description="Classification of sensor violation")
    earliest_recorded_breach: datetime = Field(..., description="First timestamp where violation was recorded (UTC)")
    breach_start: datetime = Field(..., description="Start timestamp of continuous violation interval (UTC)")
    breach_end: datetime = Field(..., description="End timestamp of continuous violation interval (UTC)")
    peak_value: float = Field(..., description="Maximum/extreme value recorded during breach")
    threshold_value: float = Field(..., description="Configured threshold that was breached")
    duration_seconds: float = Field(..., description="Duration of continuous violation in seconds")
    affected_readings_count: int = Field(..., description="Count of discrete readings violating threshold")
    affected_records_sample: List[NormalizedTelemetryReading] = Field(default_factory=list, description="Sample of violating readings")
    precision_note: str = Field(..., description="Statement regarding time resolution & precision boundaries")

class DataQualityReport(BaseModel):
    """Audit of CSV data quality and integrity."""
    total_rows_parsed: int = Field(default=0, description="Total rows parsed from CSV")
    valid_readings_count: int = Field(default=0, description="Count of successfully parsed readings")
    malformed_rows_count: int = Field(default=0, description="Count of unparseable or malformed rows")
    duplicate_timestamps_count: int = Field(default=0, description="Count of duplicate timestamps detected")
    missing_intervals_count: int = Field(default=0, description="Count of detected telemetry data gaps")
    impossible_coordinates_count: int = Field(default=0, description="Count of coordinates outside [-90,90] / [-180,180]")
    ambiguous_timezones_count: int = Field(default=0, description="Count of timestamps missing timezone info")
    quality_flags: List[str] = Field(default_factory=list, description="Summary quality alert tags")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Detailed list of detected anomalies")

class TelemetryThresholdConfig(BaseModel):
    """Configurable threshold parameters for deterministic breach detection."""
    temp_min_c: Optional[float] = Field(default=None, description="Minimum acceptable temperature in Celsius")
    temp_max_c: Optional[float] = Field(default=None, description="Maximum acceptable temperature in Celsius")
    shock_g_threshold: Optional[float] = Field(default=4.0, description="Critical shock threshold in G-force")
    humidity_max_pct: Optional[float] = Field(default=None, description="Maximum acceptable humidity percentage")
    temp_duration_tolerance_seconds: float = Field(default=0.0, description="Tolerance duration before breach is confirmed")
    expected_interval_seconds: Optional[float] = Field(default=None, description="Expected sampling interval in seconds")
    max_gap_tolerance_seconds: Optional[float] = Field(default=3600.0, description="Threshold to flag a missing telemetry interval")

class IncidentTelemetry(BaseModel):
    """Strongly typed internal forensic incident representation."""
    container_id: Optional[str] = Field(None, description="Container identifier")
    device_id: Optional[str] = Field(None, description="Sensor logger device identifier")
    has_breach: bool = Field(..., description="True if any threshold breach was detected")
    breaches: List[TelemetryBreach] = Field(default_factory=list, description="List of detected discrete breach intervals")
    data_quality: DataQualityReport = Field(..., description="Data quality and anomaly report")
    readings: List[NormalizedTelemetryReading] = Field(default_factory=list, description="Chronologically sorted normalized readings")
    earliest_recorded_breach: Optional[datetime] = Field(None, description="Overall earliest breach timestamp (UTC)")
    latest_recorded_breach: Optional[datetime] = Field(None, description="Overall latest breach timestamp (UTC)")
    sampling_resolution_seconds: Optional[float] = Field(None, description="Computed or declared sampling interval")
    precision_statement: str = Field(..., description="Explicit statement of temporal precision boundaries")
