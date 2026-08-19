import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from ..models.case import (
    CaseModel,
    CaseStatus,
    ShipmentInfo,
    SourceDocumentRef,
    TelemetryRef,
    HumanApprovalEvent,
    SettlementState,
    NegotiationMessage,
    AuditEvent
)
from ..models.investigation import DisputeInvestigationResponse
from .case_repository import FirestoreCaseRepository, CaseNotFoundError, ConcurrencyConflictError
from ..config import get_settings


class CaseService:
    """
    Business logic and lifecycle coordinator for SubroGate persistent dispute cases.
    """

    def __init__(self, repository: Optional[FirestoreCaseRepository] = None):
        self.repository = repository or FirestoreCaseRepository()
        self.settings = get_settings()

    def create_case(
        self,
        shipment_info: Optional[ShipmentInfo] = None,
        document_refs: Optional[List[SourceDocumentRef]] = None,
        telemetry_ref: Optional[TelemetryRef] = None,
        actor: str = "SYSTEM",
        initial_status: CaseStatus = CaseStatus.INGESTED,
        custom_case_id: Optional[str] = None
    ) -> CaseModel:
        """
        Creates a new dispute case with initial audit trail.
        """
        case_id = custom_case_id or f"CASE-{datetime.now(timezone.utc).year}-{uuid.uuid4().hex[:6].upper()}"
        now_dt = datetime.now(timezone.utc)

        initial_audit = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            event_type="CASE_CREATED",
            description=f"Case initialized in state '{initial_status.value}'.",
            actor=actor,
            timestamp_utc=now_dt,
            metadata={"initial_status": initial_status.value}
        )

        case = CaseModel(
            case_id=case_id,
            status=initial_status,
            shipment_info=shipment_info or ShipmentInfo(),
            source_document_refs=document_refs or [],
            telemetry_ref=telemetry_ref,
            created_at_utc=now_dt,
            updated_at_utc=now_dt,
            model_identifier=self.settings.SUBROGATE_GEMINI_MODEL,
            application_version=self.settings.APP_VERSION,
            audit_events=[initial_audit],
            version=1
        )

        return self.repository.save(case)

    def get_case(self, case_id: str) -> Optional[CaseModel]:
        """Retrieves a case by ID."""
        return self.repository.get(case_id)

    def list_cases(
        self,
        limit: int = 50,
        status: Optional[CaseStatus] = None
    ) -> List[CaseModel]:
        """Lists recent cases."""
        return self.repository.list_cases(limit=limit, status=status)

    def attach_investigation_result(
        self,
        case_id: str,
        investigation: DisputeInvestigationResponse,
        actor: str = "INVESTIGATOR_AGENT",
        expected_version: Optional[int] = None
    ) -> CaseModel:
        """
        Attaches vertical slice forensic outputs to case and marks status ASSESSMENT_READY.
        """
        current = self.repository.get(case_id)
        if not current:
            raise CaseNotFoundError(f"Case '{case_id}' does not exist.")

        audit = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            event_type="ASSESSMENT_ATTACHED",
            description=(
                f"Forensic investigation completed. Identified responsible party: "
                f"'{investigation.evidence_backed_assessment.potentially_responsible_party}'."
            ),
            actor=actor,
            timestamp_utc=datetime.now(timezone.utc),
            metadata={"has_breach": investigation.deterministic_overlap.has_breach}
        )

        updates = {
            "status": CaseStatus.ASSESSMENT_READY,
            "normalized_timeline": [e.model_dump(mode="json") for e in investigation.reconstructed_timeline],
            "assessment": investigation.evidence_backed_assessment.model_dump(mode="json"),
            "audit_events": [a.model_dump(mode="json") for a in current.audit_events] + [audit.model_dump(mode="json")]
        }

        if investigation.extracted_eir and investigation.extracted_eir.extracted_data:
            updates["extracted_custody_events"] = investigation.extracted_eir.extracted_data.model_dump(mode="json")

        return self.repository.update(case_id, updates, expected_version=expected_version)

    def transition_status(
        self,
        case_id: str,
        new_status: CaseStatus,
        actor: str = "SYSTEM",
        reason: Optional[str] = None,
        expected_version: Optional[int] = None
    ) -> CaseModel:
        """
        Transitions case lifecycle status with an immutable audit log entry.
        """
        current = self.repository.get(case_id)
        if not current:
            raise CaseNotFoundError(f"Case '{case_id}' does not exist.")

        old_status = current.status
        now_dt = datetime.now(timezone.utc)

        audit = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            event_type="STATUS_CHANGED",
            description=f"Status changed from '{old_status.value}' to '{new_status.value}'. Reason: {reason or 'Standard workflow transition'}",
            actor=actor,
            timestamp_utc=now_dt,
            metadata={"previous_status": old_status.value, "new_status": new_status.value, "reason": reason}
        )

        updates: Dict[str, Any] = {
            "status": new_status,
            "audit_events": [a.model_dump(mode="json") for a in current.audit_events] + [audit.model_dump(mode="json")]
        }

        if new_status in (CaseStatus.RESOLVED, CaseStatus.FAILED):
            updates["closed_at_utc"] = now_dt.isoformat()

        return self.repository.update(case_id, updates, expected_version=expected_version)

    def append_audit_event(
        self,
        case_id: str,
        event_type: str,
        description: str,
        actor: str = "SYSTEM",
        metadata: Optional[Dict[str, Any]] = None,
        expected_version: Optional[int] = None
    ) -> CaseModel:
        """
        Appends an arbitrary audit log event to the case.
        """
        current = self.repository.get(case_id)
        if not current:
            raise CaseNotFoundError(f"Case '{case_id}' does not exist.")

        audit = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            event_type=event_type,
            description=description,
            actor=actor,
            timestamp_utc=datetime.now(timezone.utc),
            metadata=metadata or {}
        )

        updates = {
            "audit_events": [a.model_dump(mode="json") for a in current.audit_events] + [audit.model_dump(mode="json")]
        }

        return self.repository.update(case_id, updates, expected_version=expected_version)

    def append_negotiation_message(
        self,
        case_id: str,
        message: NegotiationMessage,
        actor: str = "ADJUSTER",
        expected_version: Optional[int] = None
    ) -> CaseModel:
        """
        Appends a communication/demand letter or counter-offer to negotiation history.
        """
        current = self.repository.get(case_id)
        if not current:
            raise CaseNotFoundError(f"Case '{case_id}' does not exist.")

        audit = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            event_type="NEGOTIATION_MESSAGE_APPENDED",
            description=f"Message '{message.message_type}' sent from '{message.sender_party}' to '{message.recipient_party}'.",
            actor=actor,
            timestamp_utc=datetime.now(timezone.utc),
            metadata={"proposed_amount_usd": message.proposed_amount_usd}
        )

        new_history = [m.model_dump(mode="json") for m in current.negotiation_history] + [message.model_dump(mode="json")]
        new_audits = [a.model_dump(mode="json") for a in current.audit_events] + [audit.model_dump(mode="json")]

        updates: Dict[str, Any] = {
            "negotiation_history": new_history,
            "audit_events": new_audits
        }

        # If approved, move to negotiation state
        if current.status == CaseStatus.APPROVED:
            updates["status"] = CaseStatus.NEGOTIATION

        return self.repository.update(case_id, updates, expected_version=expected_version)

    def record_human_approval(
        self,
        case_id: str,
        approval: HumanApprovalEvent,
        actor: str = "ADJUSTER",
        expected_version: Optional[int] = None
    ) -> CaseModel:
        """
        Records human claims adjuster sign-off and locks approved liability allocation.
        """
        current = self.repository.get(case_id)
        if not current:
            raise CaseNotFoundError(f"Case '{case_id}' does not exist.")

        audit = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:6].upper()}",
            event_type="HUMAN_APPROVAL_GRANTED",
            description=(
                f"Claims adjuster '{approval.adjuster_name}' approved liability at "
                f"{approval.allocated_liability_pct:.1f}%. Token: '{approval.audit_badge_token}'."
            ),
            actor=actor,
            timestamp_utc=datetime.now(timezone.utc),
            metadata={
                "adjuster": approval.adjuster_name,
                "liability_pct": approval.allocated_liability_pct,
                "token": approval.audit_badge_token
            }
        )

        updates = {
            "status": CaseStatus.APPROVED,
            "human_approvals": [a.model_dump(mode="json") for a in current.human_approvals] + [approval.model_dump(mode="json")],
            "audit_events": [a.model_dump(mode="json") for a in current.audit_events] + [audit.model_dump(mode="json")]
        }

        return self.repository.update(case_id, updates, expected_version=expected_version)
