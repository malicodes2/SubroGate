import os
import time
import uuid
import logging
import threading
from typing import Dict, Any, List, Optional, Sequence
from contextlib import contextmanager
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# OpenTelemetry standard imports
from opentelemetry import trace
from opentelemetry.trace import Tracer, StatusCode
from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.resources import Resource

logger = logging.getLogger("subrogate.observability")


class OperationalSpanEvent(BaseModel):
    """Safe operational event representation for UI Execution Trace display."""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str] = None
    step_name: str
    category: str = "WORKFLOW"
    start_time_utc: str
    end_time_utc: str
    duration_ms: float
    status: str = "SUCCESS"  # SUCCESS | FAILED
    case_id: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None


class InMemoryTraceBuffer(SpanExporter):
    """
    Thread-safe circular in-memory buffer capturing OpenTelemetry spans
    for local querying and real-time frontend execution trace visualization.
    """
    def __init__(self, max_spans: int = 500):
        self._spans: List[OperationalSpanEvent] = []
        self._max_spans = max_spans
        self._lock = threading.RLock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            for span in spans:
                try:
                    trace_id = format(span.context.trace_id, "032x")
                    span_id = format(span.context.span_id, "016x")
                    parent_span_id = format(span.parent.span_id, "016x") if span.parent else None
                    
                    start_sec = span.start_time / 1e9
                    end_sec = (span.end_time or time.time_ns()) / 1e9
                    duration_ms = round((end_sec - start_sec) * 1000, 2)
                    
                    start_dt = datetime.fromtimestamp(start_sec, tz=timezone.utc).isoformat()
                    end_dt = datetime.fromtimestamp(end_sec, tz=timezone.utc).isoformat()
                    
                    status = "SUCCESS"
                    error_msg = None
                    if span.status.status_code == StatusCode.ERROR:
                        status = "FAILED"
                        error_msg = span.status.description
                    
                    # Sanitize attributes to ensure zero chain-of-thought exposure
                    safe_attrs: Dict[str, Any] = {}
                    case_id = None
                    category = "WORKFLOW"
                    
                    if span.attributes:
                        for k, v in span.attributes.items():
                            # Never include raw model prompt traces or private reasoning
                            if any(secret_k in k.lower() for secret_k in ["prompt", "chain_of_thought", "reasoning", "raw_llm_response"]):
                                continue
                            if k == "case_id":
                                case_id = str(v)
                            elif k == "category":
                                category = str(v)
                            safe_attrs[k] = v
                    
                    event = OperationalSpanEvent(
                        span_id=span_id,
                        trace_id=trace_id,
                        parent_span_id=parent_span_id,
                        step_name=span.name,
                        category=category,
                        start_time_utc=start_dt,
                        end_time_utc=end_dt,
                        duration_ms=duration_ms,
                        status=status,
                        case_id=case_id,
                        attributes=safe_attrs,
                        error_message=error_msg
                    )
                    
                    self._spans.append(event)
                    if len(self._spans) > self._max_spans:
                        self._spans.pop(0)
                except Exception as ex:
                    logger.debug("Failed to record span in memory buffer: %s", ex)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True

    def get_all_spans(self) -> List[OperationalSpanEvent]:
        with self._lock:
            return list(self._spans)

    def get_spans_for_case(self, case_id: str) -> List[OperationalSpanEvent]:
        with self._lock:
            return [s for s in self._spans if s.case_id == case_id]

    def clear(self) -> None:
        with self._lock:
            self._spans.clear()


class SubroGateObservability:
    """
    Production-style OpenTelemetry orchestrator.
    Configures OpenTelemetry TracerProvider, CloudTraceSpanExporter (if configured),
    and local in-memory trace buffer.
    """
    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SubroGateObservability, cls).__new__(cls)
                cls._instance._init_telemetry()
            return cls._instance

    def _init_telemetry(self):
        self.service_name = "subrogate-backend"
        self.resource = Resource.create({"service.name": self.service_name, "service.version": "1.0.0"})
        self.provider = TracerProvider(resource=self.resource)
        
        # 1. In-Memory Trace Buffer (always active for UI and local debug)
        self.memory_buffer = InMemoryTraceBuffer(max_spans=1000)
        self.provider.add_span_processor(SimpleSpanProcessor(self.memory_buffer))
        
        # 2. Google Cloud Trace Exporter (active if GCP Project or Credentials configured)
        self.gcp_trace_active = False
        gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
        if gcp_project or os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            try:
                # Dynamic import for CloudTraceSpanExporter to allow optional GCP installation
                from opentelemetry.exporter.gcp_trace import CloudTraceSpanExporter  # type: ignore
                cloud_exporter = CloudTraceSpanExporter(project_id=gcp_project or None)
                self.provider.add_span_processor(SimpleSpanProcessor(cloud_exporter))
                self.gcp_trace_active = True
                logger.info("Google Cloud Trace OpenTelemetry exporter active for project: %s", gcp_project or "default")
            except Exception as e:
                logger.info("Google Cloud Trace exporter not initialized (falling back to memory trace buffer): %s", e)
        
        trace.set_tracer_provider(self.provider)
        self.tracer: Tracer = trace.get_tracer("subrogate.tracer", "1.0.0")

    def get_tracer(self) -> Tracer:
        return self.tracer

    def get_spans(self, case_id: Optional[str] = None) -> List[OperationalSpanEvent]:
        if case_id:
            return self.memory_buffer.get_spans_for_case(case_id)
        return self.memory_buffer.get_all_spans()

    def get_spans_for_case(self, case_id: str) -> List[OperationalSpanEvent]:
        return self.memory_buffer.get_spans_for_case(case_id)

    def record_manual_span(
        self,
        step_name: str,
        case_id: Optional[str],
        duration_ms: float,
        status: str = "SUCCESS",
        category: str = "WORKFLOW",
        attributes: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> OperationalSpanEvent:
        """Manually records an operational event for cases initialized via fixtures/demo loaders."""
        now = datetime.now(timezone.utc).isoformat()
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        
        event = OperationalSpanEvent(
            span_id=span_id,
            trace_id=trace_id,
            step_name=step_name,
            category=category,
            start_time_utc=now,
            end_time_utc=now,
            duration_ms=duration_ms,
            status=status,
            case_id=case_id,
            attributes=attributes or {},
            error_message=error_message
        )
        with self.memory_buffer._lock:
            self.memory_buffer._spans.append(event)
        return event


# Global Singleton Instance
observability = SubroGateObservability()
tracer = observability.get_tracer()


@contextmanager
def trace_span(
    name: str,
    case_id: Optional[str] = None,
    category: str = "WORKFLOW",
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Context manager for instrumenting code blocks with OpenTelemetry spans.
    Captures duration, attributes, and errors automatically without exposing model chain-of-thought.
    """
    span_attrs: Dict[str, Any] = {}
    if attributes:
        for k, v in attributes.items():
            if isinstance(v, (str, bool, int, float)):
                span_attrs[k] = v
            else:
                span_attrs[k] = str(v)

    if case_id:
        span_attrs["case_id"] = str(case_id)
    span_attrs["category"] = str(category)
    
    with tracer.start_as_current_span(name, attributes=span_attrs) as span:
        try:
            yield span
            span.set_status(StatusCode.OK)
        except Exception as e:
            span.set_status(StatusCode.ERROR, str(e))
            span.set_attribute("error.type", type(e).__name__)
            span.set_attribute("error.message", str(e))
            raise
