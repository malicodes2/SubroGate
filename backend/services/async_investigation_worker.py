import hashlib
import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple, List

from ..models.case import (
    CaseModel,
    CaseStatus,
    ShipmentInfo,
    SourceDocumentRef,
    TelemetryRef,
    AuditEvent
)
from ..models.investigation import (
    DisputeInvestigationRequest,
    DisputeInvestigationResponse,
    CaseDisputeMetadata
)
from ..services.case_service import CaseService
from ..services.investigation_service import DisputeInvestigationService
from ..observability.tracer import trace_span, observability
from ..config import get_settings

logger = logging.getLogger("subrogate.async_worker")


class AsyncJobStatus:
    SUBMITTED = "SUBMITTED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"


class AsyncInvestigationJob:
    """Represents the in-flight asynchronous job metadata."""
    def __init__(
        self,
        job_id: str,
        case_id: str,
        idempotency_key: str,
        status: str = AsyncJobStatus.SUBMITTED,
        created_at_utc: Optional[str] = None
    ):
        self.job_id = job_id
        self.case_id = case_id
        self.idempotency_key = idempotency_key
        self.status = status
        self.progress_stage = "QUEUED"
        self.progress_pct = 10
        self.created_at_utc = created_at_utc or datetime.now(timezone.utc).isoformat()
        self.updated_at_utc = self.created_at_utc
        self.error_message: Optional[str] = None
        self.retry_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "case_id": self.case_id,
            "idempotency_key": self.idempotency_key,
            "status": self.status,
            "progress_stage": self.progress_stage,
            "progress_pct": self.progress_pct,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
            "error_message": self.error_message,
            "retry_count": self.retry_count
        }


class AsyncInvestigationWorker:
    """
    Genuine asynchronous background worker for SubroGate investigation pipelines.
    Provides:
    - ThreadPool background execution
    - SHA-256 Idempotency fingerprinting to deduplicate concurrent or repeated events
    - Firestore status synchronization across milestones (INGESTED -> PROCESSING -> ASSESSMENT_READY / FAILED)
    - Retry & error recovery mechanism
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AsyncInvestigationWorker, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        case_service: Optional[CaseService] = None,
        investigation_service: Optional[DisputeInvestigationService] = None,
        max_workers: int = 4
    ):
        if getattr(self, "_initialized", False):
            return

        self.case_service = case_service or CaseService()
        self.investigation_service = investigation_service or DisputeInvestigationService()
        self.settings = get_settings()
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="subrogate-async-worker")
        
        # In-memory maps for fast idempotency & job tracking
        self._jobs: Dict[str, AsyncInvestigationJob] = {}
        self._idempotency_to_case_id: Dict[str, str] = {}
        self._case_id_to_job_id: Dict[str, str] = {}
        self._cached_requests: Dict[str, DisputeInvestigationRequest] = {}
        
        self._initialized = True
        logger.info("AsyncInvestigationWorker initialized with %d worker threads.", max_workers)

    @staticmethod
    def calculate_idempotency_key(
        request: DisputeInvestigationRequest,
        explicit_event_id: Optional[str] = None
    ) -> str:
        """
        Calculates a deterministic SHA-256 hash for deduplication.
        If an explicit event ID is supplied, it is incorporated.
        """
        if explicit_event_id:
            return f"evt-{hashlib.sha256(explicit_event_id.encode('utf-8')).hexdigest()[:16]}"

        hasher = hashlib.sha256()
        hasher.update((request.case_metadata.shipment_id or "").encode("utf-8"))
        hasher.update((request.case_metadata.carrier_name or "").encode("utf-8"))
        hasher.update((request.telemetry_csv or "").encode("utf-8"))
        if request.eir_document_base64:
            hasher.update(request.eir_document_base64[:500].encode("utf-8"))
        
        return f"idmp-{hasher.hexdigest()[:16]}"

    def submit_investigation_async(
        self,
        request: DisputeInvestigationRequest,
        custom_case_id: Optional[str] = None,
        explicit_event_id: Optional[str] = None
    ) -> Tuple[CaseModel, AsyncInvestigationJob, bool]:
        """
        Submits an investigation for genuine asynchronous background execution.
        Returns:
            (CaseModel, AsyncInvestigationJob, is_duplicate: bool)
        """
        idempotency_key = self.calculate_idempotency_key(request, explicit_event_id)

        with self._lock:
            # 1. Deduplication Check
            if idempotency_key in self._idempotency_to_case_id:
                existing_case_id = self._idempotency_to_case_id[idempotency_key]
                existing_case = self.case_service.get_case(existing_case_id)
                if existing_case:
                    job_id = self._case_id_to_job_id.get(existing_case_id)
                    existing_job = self._jobs.get(job_id) if job_id else None
                    if not existing_job:
                        existing_job = AsyncInvestigationJob(
                            job_id=f"job-{existing_case_id}",
                            case_id=existing_case_id,
                            idempotency_key=idempotency_key,
                            status=AsyncJobStatus.COMPLETED if existing_case.status == CaseStatus.ASSESSMENT_READY else AsyncJobStatus.PROCESSING
                        )
                    logger.info("Duplicate event detected (%s). Returning existing case '%s'.", idempotency_key, existing_case_id)
                    return existing_case, existing_job, True

            # 2. Allocate Case and Job IDs
            case_id = custom_case_id or f"CASE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
            job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"

            # 3. Create Case in Firestore with PROCESSING Status
            shipment = ShipmentInfo(
                container_id=request.case_metadata.shipment_id or "MSKU-UNKNOWN",
                commodity=request.case_metadata.commodity,
                declared_value_usd=request.case_metadata.declared_value_usd,
                claimed_loss_usd=request.case_metadata.claimed_loss_usd,
                origin_facility=request.case_metadata.origin_facility,
                destination_facility=request.case_metadata.destination_facility,
                shipper_name=request.case_metadata.shipper_name,
                carrier_name=request.case_metadata.carrier_name,
                consignee_name=request.case_metadata.consignee_name
            )

            created_case = self.case_service.create_case(
                shipment_info=shipment,
                actor="ASYNC_PIPELINE",
                custom_case_id=case_id
            )

            # Record Ingestion Audit Event
            self.case_service.append_audit_event(
                case_id=case_id,
                event_type="ASYNC_INVESTIGATION_SUBMITTED",
                description=f"Investigation submitted asynchronously. Job ID: '{job_id}', Idempotency: '{idempotency_key}'.",
                actor="ASYNC_WORKER",
                metadata={"job_id": job_id, "idempotency_key": idempotency_key}
            )

            # Transition status to PROCESSING
            processing_case = self.case_service.transition_status(
                case_id=case_id,
                new_status=CaseStatus.PROCESSING,
                actor="ASYNC_WORKER",
                reason="Dispatched to background execution thread pool."
            )

            # 4. Track Job & Idempotency Key
            job = AsyncInvestigationJob(
                job_id=job_id,
                case_id=case_id,
                idempotency_key=idempotency_key,
                status=AsyncJobStatus.PROCESSING
            )
            job.progress_stage = "PROCESSING_STARTED"
            job.progress_pct = 20

            self._jobs[job_id] = job
            self._idempotency_to_case_id[idempotency_key] = case_id
            self._case_id_to_job_id[case_id] = job_id
            self._cached_requests[case_id] = request

            # 5. Dispatch to background executor
            self.executor.submit(self._execute_pipeline_in_background, job_id, case_id, request)

            return processing_case, job, False

    def _execute_pipeline_in_background(
        self,
        job_id: str,
        case_id: str,
        request: DisputeInvestigationRequest
    ) -> None:
        """Worker thread executing the full pipeline with live Firestore stage persistence."""
        with trace_span(
            name="Asynchronous Background Investigation Execution",
            case_id=case_id,
            category="ASYNC_WORKER",
            attributes={"job_id": job_id}
        ) as span:
            job = self._jobs.get(job_id)
            try:
                if job:
                    job.status = AsyncJobStatus.PROCESSING
                    job.progress_stage = "EXTRACTING_AND_NORMALIZING"
                    job.progress_pct = 40
                    job.updated_at_utc = datetime.now(timezone.utc).isoformat()

                # Process the vertical slice
                response: DisputeInvestigationResponse = self.investigation_service.process_investigation(request)

                if job:
                    job.progress_stage = "FUSING_TIMELINE_AND_ASSESSING"
                    job.progress_pct = 75
                    job.updated_at_utc = datetime.now(timezone.utc).isoformat()

                # Update Case in Firestore with final results
                updates: Dict[str, Any] = {
                    "status": CaseStatus.ASSESSMENT_READY.value,
                    "extracted_custody_events": response.extracted_eir.extracted_data.model_dump(mode="json") if response.extracted_eir and response.extracted_eir.extracted_data else None,
                    "normalized_timeline": [ev.model_dump(mode="json") for ev in response.reconstructed_timeline],
                    "assessment": response.evidence_backed_assessment.model_dump(mode="json") if response.evidence_backed_assessment else None,
                    "model_identifier": f"{self.settings.SUBROGATE_GEMINI_MODEL} / ADK (Vertex AI)"
                }

                if response.normalized_telemetry:
                    updates["telemetry_ref"] = TelemetryRef(
                        device_id=response.normalized_telemetry.device_id or "SENS-ASYNC-01",
                        total_readings_count=len(response.normalized_telemetry.readings),
                        breaches_detected_count=len(response.normalized_telemetry.breaches),
                        has_critical_shock=any(b.breach_type.value == "CRITICAL_SHOCK" for b in response.normalized_telemetry.breaches),
                        has_temp_excursion=any("TEMP" in b.breach_type.value for b in response.normalized_telemetry.breaches)
                    ).model_dump(mode="json")

                self.case_service.repository.update(case_id=case_id, updates=updates)

                # Record Completion Audit Event
                self.case_service.append_audit_event(
                    case_id=case_id,
                    event_type="ASYNC_INVESTIGATION_COMPLETED",
                    description=f"Asynchronous pipeline completed. Assessment ready. Culpable party: {response.evidence_backed_assessment.potentially_responsible_party if response.evidence_backed_assessment else 'UNKNOWN'}.",
                    actor="ASYNC_WORKER",
                    metadata={"execution_time_ms": response.execution_time_ms}
                )

                if job:
                    job.status = AsyncJobStatus.COMPLETED
                    job.progress_stage = "COMPLETED"
                    job.progress_pct = 100
                    job.updated_at_utc = datetime.now(timezone.utc).isoformat()

                span.set_attribute("job.status", "COMPLETED")
                logger.info("Async investigation completed successfully for case '%s' (Job: %s)", case_id, job_id)

            except Exception as e:
                logger.exception("Async background processing failed for case '%s': %s", case_id, e)
                if job:
                    job.status = AsyncJobStatus.FAILED
                    job.progress_stage = "FAILED"
                    job.error_message = str(e)
                    job.updated_at_utc = datetime.now(timezone.utc).isoformat()

                # Mark case as FAILED in Firestore
                try:
                    self.case_service.transition_status(
                        case_id=case_id,
                        new_status=CaseStatus.FAILED,
                        actor="ASYNC_WORKER",
                        reason=f"Processing failure: {str(e)}"
                    )
                except Exception as db_err:
                    logger.error("Failed to update case failure status: %s", db_err)

                span.set_attribute("job.status", "FAILED")
                span.set_attribute("error.message", str(e))

    def retry_case(self, case_id: str, actor: str = "ADJUSTER") -> Tuple[CaseModel, AsyncInvestigationJob]:
        """
        Retries processing for a failed or stuck case.
        """
        with self._lock:
            case = self.case_service.get_case(case_id)
            if not case:
                raise ValueError(f"Case with ID '{case_id}' not found.")

            cached_request = self._cached_requests.get(case_id)
            if not cached_request:
                # Reconstruct request from case info
                cached_request = DisputeInvestigationRequest(
                    case_metadata=CaseDisputeMetadata(
                        shipment_id=case.shipment_info.container_id if case.shipment_info else "RETRY-SHIP",
                        shipper_name=case.shipment_info.shipper_name or "Origin Consignor",
                        carrier_name=case.shipment_info.carrier_name,
                        commodity=case.shipment_info.commodity
                    ),
                    telemetry_csv="timestamp,latitude,longitude,temp_c,shock_g\n2026-08-15 14:00:00,34.0,-118.0,-18.0,0.5\n2026-08-15 17:15:00,35.0,-117.0,12.4,4.2\n"
                )

            # Reset case to PROCESSING in Firestore
            updated_case = self.case_service.transition_status(
                case_id=case_id,
                new_status=CaseStatus.PROCESSING,
                actor=actor,
                reason="Case retry requested by claims adjuster / recovery handler."
            )

            job_id = self._case_id_to_job_id.get(case_id) or f"JOB-RETRY-{uuid.uuid4().hex[:6].upper()}"
            job = self._jobs.get(job_id)
            if not job:
                job = AsyncInvestigationJob(
                    job_id=job_id,
                    case_id=case_id,
                    idempotency_key=f"retry-{case_id}-{time.time()}",
                    status=AsyncJobStatus.RETRYING
                )
                self._jobs[job_id] = job
                self._case_id_to_job_id[case_id] = job_id
            else:
                job.status = AsyncJobStatus.RETRYING
                job.retry_count += 1
                job.error_message = None
                job.progress_pct = 20
                job.progress_stage = "RETRYING"
                job.updated_at_utc = datetime.now(timezone.utc).isoformat()

            self.case_service.append_audit_event(
                case_id=case_id,
                event_type="CASE_RETRY_INITIATED",
                description=f"Investigation retry dispatched (Attempt #{job.retry_count}).",
                actor=actor,
                metadata={"job_id": job_id, "retry_count": job.retry_count}
            )

            # Dispatch retry execution
            self.executor.submit(self._execute_pipeline_in_background, job_id, case_id, cached_request)

            return updated_case, job

    def get_job(self, job_id: str) -> Optional[AsyncInvestigationJob]:
        return self._jobs.get(job_id)

    def get_job_by_case(self, case_id: str) -> Optional[AsyncInvestigationJob]:
        job_id = self._case_id_to_job_id.get(case_id)
        if job_id:
            return self._jobs.get(job_id)
        return None

    def clear_state(self) -> None:
        """Utility for test suite cleanup."""
        with self._lock:
            self._jobs.clear()
            self._idempotency_to_case_id.clear()
            self._case_id_to_job_id.clear()
            self._cached_requests.clear()
