import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from ..models.security import SecurityScreeningReport, SecurityVerdict
from ..models.settlement import OutboundDraft
from .security_engine import BaseSecurityScreeningEngine, DeterministicSecurityScreeningEngine, GoogleModelArmorAdapter
from .case_service import CaseService
from ..observability.tracer import trace_span

logger = logging.getLogger("subrogate.security.service")


class SecurityScreeningService:
    """
    Coordinates security gate inspections, audit logging in Firestore,
    and sanitized suggestion management.
    """

    def __init__(
        self,
        engine: Optional[BaseSecurityScreeningEngine] = None,
        case_service: Optional[CaseService] = None
    ):
        self.engine = engine or DeterministicSecurityScreeningEngine()
        self.case_service = case_service or CaseService()

    def screen_draft(
        self,
        draft: OutboundDraft,
        case_id: str,
        actor: str = "SECURITY_GATE"
    ) -> SecurityScreeningReport:
        """
        Executes security screening over an outbound draft.
        Saves an immutable audit trail in Firestore without exposing raw secrets.
        """
        engine_name = getattr(self.engine, "ENGINE_ID", getattr(self.engine, "ENGINE_NAME", "DETERMINISTIC_LOCAL_ENGINE"))
        with trace_span(
            name="Google Model Armor Security Screening",
            case_id=case_id,
            category="MODEL_ARMOR",
            attributes={
                "draft_id": draft.draft_id,
                "engine_used": engine_name,
                "actor": actor
            }
        ) as span:
            report = self.engine.screen_text(
                text=draft.draft_body_markdown,
                case_id=case_id,
                draft_id=draft.draft_id
            )
            span.set_attribute("security.verdict", report.verdict.value)
            span.set_attribute("security.findings_count", report.findings_count)

        # Log security audit event in Firestore
        categories = list({f.category.value for f in report.findings})
        try:
            self.case_service.append_audit_event(
                case_id=case_id,
                event_type="SECURITY_SCREENING_COMPLETED",
                description=f"Security Gate verdict: '{report.verdict.value}' (Engine: {report.engine_used}). Action: {report.action_taken}",
                actor=actor,
                metadata={
                    "screening_id": report.screening_id,
                    "draft_id": draft.draft_id,
                    "verdict": report.verdict.value,
                    "engine_used": report.engine_used,
                    "findings_count": report.findings_count,
                    "detected_categories": categories,
                    "action_taken": report.action_taken
                }
            )
        except Exception as e:
            logger.warning(f"Could not persist security audit event for case '{case_id}': {e}")

        return report
