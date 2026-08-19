import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..models.settlement import (
    CarrierObjectionType,
    InboundCarrierMessage,
    OutboundDraft,
    DraftApprovalStatus,
    SimulationTurn,
    ThreeTurnNegotiationResult
)
from ..models.case import CaseModel, CaseStatus, SettlementState, HumanApprovalEvent
from .case_service import CaseService


class CarrierSimulator:
    """
    Deterministic simulated carrier inbox providing realistic defense letters
    and multi-turn negotiation simulations.
    """

    SAMPLE_OBJECTIONS: Dict[CarrierObjectionType, Dict[str, str]] = {
        CarrierObjectionType.DAMAGE_BEFORE_PICKUP: {
            "subject": "RE: Cargo Claim Rejection - Alleged Damage Prior to Carrier Receipt",
            "body": (
                "We have investigated your formal notice of subrogation claim. Based on our driver's report, "
                "the cargo was already thawed and damaged prior to our pickup at the origin facility. "
                "The shipper failed to properly pre-cool the container. Consequently, we must decline liability."
            )
        },
        CarrierObjectionType.DISPUTES_CUSTODY: {
            "subject": "RE: Formal Notice of Claim - Custody Disclaimer",
            "body": (
                "Our records show that the container was delayed at the rail/marine terminal. "
                "We did not maintain Care, Custody, and Control at the time when the cargo temperature/shock "
                "occurred. We advise you to direct your subrogation demand to the terminal operator."
            )
        },
        CarrierObjectionType.DISPUTES_SENSOR_RELIABILITY: {
            "subject": "RE: Telemetry Data Challenge - Uncertified Sensor",
            "body": (
                "We have reviewed the submitted temperature graph. The data log appears to originate from an "
                "uncalibrated, customer-installed third-party logger. We do not accept unverified sensor logs "
                "as evidence of carrier negligence without NIST calibration records."
            )
        },
        CarrierObjectionType.NOTICE_ALLEGEDLY_LATE: {
            "subject": "RE: Claim Notice Rejection - Statutory Time Bar",
            "body": (
                "Please be advised that your formal notice of subrogation claim was received past our standard "
                "contractual notice deadline. We consider this claim time-barred under our bill of lading terms."
            )
        },
        CarrierObjectionType.REQUESTS_SUPPORTING_DOCS: {
            "subject": "RE: Subrogation Claim Review - Request for Verification Documents",
            "body": (
                "We are evaluating your claim. Before our claims committee can authorize any settlement discussion, "
                "please provide: (1) signed origin Equipment Interchange Receipt (EIR), (2) calibrated raw CSV telemetry, "
                "and (3) certified commercial cargo salvage and destruction invoices."
            )
        },
        CarrierObjectionType.PARTIAL_SETTLEMENT_OFFER: {
            "subject": "RE: Compromise Settlement Proposal",
            "body": (
                "In review of the supporting EIR and telemetry records, and without admission of liability, "
                "our legal claims committee is authorized to offer a commercial compromise payment of $45,000.00 USD "
                "in full and final resolution of all claims regarding this shipment."
            )
        }
    }

    @classmethod
    def generate_inbound_message(
        cls,
        case_id: str,
        objection_type: CarrierObjectionType,
        carrier_name: str = "Apex Drayage LLC",
        offered_amount_usd: Optional[float] = None
    ) -> InboundCarrierMessage:
        """
        Generates a realistic inbound carrier communication matching the specified objection.
        """
        template = cls.SAMPLE_OBJECTIONS.get(
            objection_type,
            cls.SAMPLE_OBJECTIONS[CarrierObjectionType.DAMAGE_BEFORE_PICKUP]
        )

        return InboundCarrierMessage(
            message_id=f"IN-MSG-{uuid.uuid4().hex[:6].upper()}",
            case_id=case_id,
            sender_party=f"{carrier_name} Claims Dept",
            sender_email=f"claims@{carrier_name.lower().replace(' ', '')}.com",
            subject=f"{template['subject']} (Ref: {case_id})",
            body_text=template["body"],
            offered_amount_usd=offered_amount_usd or (45000.0 if objection_type == CarrierObjectionType.PARTIAL_SETTLEMENT_OFFER else None),
            identified_objection=objection_type,
            received_at_utc=datetime.now(timezone.utc)
        )
