import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from ..models.investigation import CaseDisputeMetadata, DisputeInvestigationRequest
from ..models.telemetry import TelemetryThresholdConfig


class SimulatedTelemetryEvent(BaseModel):
    """Represents a simulated IoT edge sensor transmission event."""
    event_id: str = Field(..., description="Unique event message ID")
    device_id: str = Field(default="SENS-SIM-9000", description="Sensor logger ID")
    container_id: str = Field(default="MSKU9082345", description="Container unit number")
    event_type: str = Field(default="BREACH_ALERT", description="Event classification")
    csv_payload: str = Field(..., description="CSV payload snippet")
    occurred_at_utc: str = Field(..., description="Timestamp of sensor reading in UTC")
    is_breach: bool = Field(default=True, description="Whether payload contains threshold breach")


class TelemetryEventSimulator:
    """
    Lightweight IoT sensor telemetry event generator and publisher for demo cases.
    Enables realistic streaming simulation without external hardware or producers.
    """

    @classmethod
    def generate_shock_breach_event(
        cls,
        container_id: str = "MSKU9082345",
        device_id: str = "SENS-LOG-8891",
        event_id: Optional[str] = None
    ) -> SimulatedTelemetryEvent:
        """Generates an impact / shock breach event (4.2G) occurring post-interchange."""
        evt_id = event_id or f"EVT-SHK-{uuid.uuid4().hex[:6].upper()}"
        base_time = datetime(2026, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        csv_rows = ["timestamp,latitude,longitude,temp_c,shock_g"]
        # Pre-breach normal
        for i in range(4):
            t = base_time + timedelta(minutes=i * 45)
            csv_rows.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')},33.74,-118.28,-18.2,0.4")
        
        # Breach event at 17:15 UTC (3h 15m after handover)
        breach_t = base_time + timedelta(hours=3, minutes=15)
        csv_rows.append(f"{breach_t.strftime('%Y-%m-%d %H:%M:%S')},34.89,-117.02,-17.8,4.2")
        
        # Post-breach
        for i in range(1, 4):
            t = breach_t + timedelta(minutes=i * 30)
            csv_rows.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')},35.12,-116.80,-17.5,0.6")

        return SimulatedTelemetryEvent(
            event_id=evt_id,
            device_id=device_id,
            container_id=container_id,
            event_type="CRITICAL_SHOCK_EXCURSION",
            csv_payload="\n".join(csv_rows),
            occurred_at_utc=breach_t.isoformat(),
            is_breach=True
        )

    @classmethod
    def generate_temperature_excursion_event(
        cls,
        container_id: str = "MSKU9082345",
        device_id: str = "SENS-REEFER-4412",
        event_id: Optional[str] = None
    ) -> SimulatedTelemetryEvent:
        """Generates a reefer thermal excursion event (+12.4°C vs -18.0°C setpoint)."""
        evt_id = event_id or f"EVT-TMP-{uuid.uuid4().hex[:6].upper()}"
        base_time = datetime(2026, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        csv_rows = ["timestamp,latitude,longitude,temp_c,shock_g"]
        # Normal cold chain
        for i in range(3):
            t = base_time + timedelta(hours=i)
            csv_rows.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')},34.05,-118.25,-18.0,0.2")
        
        # Thermal failure breach (+12.4 C)
        breach_t = base_time + timedelta(hours=4)
        csv_rows.append(f"{breach_t.strftime('%Y-%m-%d %H:%M:%S')},34.90,-116.90,12.4,0.3")
        
        # Lingering warm temp
        for i in range(1, 3):
            t = breach_t + timedelta(hours=i)
            csv_rows.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')},35.20,-116.50,11.8,0.2")

        return SimulatedTelemetryEvent(
            event_id=evt_id,
            device_id=device_id,
            container_id=container_id,
            event_type="THERMAL_DEFROST_FAILURE",
            csv_payload="\n".join(csv_rows),
            occurred_at_utc=breach_t.isoformat(),
            is_breach=True
        )

    @classmethod
    def generate_nominal_clean_event(
        cls,
        container_id: str = "MSKU9082345",
        device_id: str = "SENS-LOG-1100",
        event_id: Optional[str] = None
    ) -> SimulatedTelemetryEvent:
        """Generates clean sensor data with no breaches."""
        evt_id = event_id or f"EVT-CLN-{uuid.uuid4().hex[:6].upper()}"
        base_time = datetime(2026, 8, 15, 14, 0, 0, tzinfo=timezone.utc)
        
        csv_rows = ["timestamp,latitude,longitude,temp_c,shock_g"]
        for i in range(8):
            t = base_time + timedelta(hours=i)
            csv_rows.append(f"{t.strftime('%Y-%m-%d %H:%M:%S')},34.05,-118.25,-18.1,0.3")

        return SimulatedTelemetryEvent(
            event_id=evt_id,
            device_id=device_id,
            container_id=container_id,
            event_type="PERIODIC_HEARTBEAT",
            csv_payload="\n".join(csv_rows),
            occurred_at_utc=base_time.isoformat(),
            is_breach=False
        )

    @classmethod
    def create_investigation_request_from_event(
        cls,
        event: SimulatedTelemetryEvent,
        carrier_name: str = "Apex Drayage Logistics LLC",
        shipper_name: str = "Pacific Pharma Global Inc.",
        claimed_loss_usd: float = 75000.0
    ) -> DisputeInvestigationRequest:
        """Constructs a complete DisputeInvestigationRequest from a simulated sensor event."""
        return DisputeInvestigationRequest(
            case_metadata=CaseDisputeMetadata(
                shipment_id=event.container_id,
                shipper_name=shipper_name,
                carrier_name=carrier_name,
                consignee_name="Midwest Cold Chain Medical Inc.",
                commodity="Frozen Pharmaceutical Vaccines",
                declared_value_usd=100000.0,
                claimed_loss_usd=claimed_loss_usd,
                origin_facility="APM Terminals Pier 400 Los Angeles, CA",
                destination_facility="Midwest Health Distribution Chicago, IL",
                governing_regime="Carmack Amendment"
            ),
            telemetry_csv=event.csv_payload,
            thresholds=TelemetryThresholdConfig(
                shock_g_threshold=4.0,
                temp_max_c=-10.0,
                temp_min_c=-25.0
            )
        )
