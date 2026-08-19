import hashlib
import time
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone

from ..models.documents import (
    DocumentMetadata,
    EIRExtractionResult,
    ExtractionStatus,
    ExtractedEIRData,
    DocumentValidationReport
)
from ..agents.document_agent import DocumentIntelligenceAgent
from .document_validator import DocumentValidator
from ..config import get_settings
from ..observability.tracer import trace_span


class DocumentIntelligenceService:
    """
    Orchestration service for cargo document ingestion, multimodal extraction,
    deterministic validation, and evidence preservation.
    """

    ALLOWED_MIME_TYPES = {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
        "image/tiff",
    }

    MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB

    def __init__(self, agent: Optional[DocumentIntelligenceAgent] = None):
        self.agent = agent or DocumentIntelligenceAgent()
        self.settings = get_settings()

    @classmethod
    def compute_sha256(cls, file_bytes: bytes) -> str:
        """Computes cryptographic SHA-256 fingerprint of file bytes."""
        return hashlib.sha256(file_bytes).hexdigest()

    def process_document(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        expected_container_id: Optional[str] = None,
        expected_carrier: Optional[str] = None,
        default_timezone: Optional[str] = None,
        mock_extraction: Optional[ExtractedEIRData] = None
    ) -> EIRExtractionResult:
        """
        Executes end-to-end extraction and validation on a document file.
        """
        start_time = time.time()
        file_size = len(file_bytes)
        sha256 = self.compute_sha256(file_bytes)
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

        # Clean/normalize MIME type
        clean_mime = mime_type.lower().split(';')[0].strip()
        if clean_mime not in self.ALLOWED_MIME_TYPES:
            # Fallback based on filename extension
            if filename.lower().endswith(".pdf"):
                clean_mime = "application/pdf"
            elif filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".tiff")):
                clean_mime = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            else:
                report = DocumentValidationReport(
                    status=ExtractionStatus.FAILED,
                    requires_human_verification=True,
                    errors=[f"Unsupported MIME type: '{mime_type}'. Supported: {', '.join(sorted(self.ALLOWED_MIME_TYPES))}"],
                    warnings=[],
                    is_timestamp_parseable=False,
                    is_timezone_explicit=False,
                    is_container_id_valid_iso=False,
                    container_id_checksum_matches=False,
                    timestamp_has_supporting_evidence=False
                )
                metadata = DocumentMetadata(
                    document_id=doc_id,
                    filename=filename,
                    file_size_bytes=file_size,
                    mime_type=mime_type,
                    sha256_hash=sha256,
                    total_pages=1
                )
                return EIRExtractionResult(
                    document_metadata=metadata,
                    extraction_status=ExtractionStatus.FAILED,
                    extracted_data=None,
                    validation_report=report,
                    model_name_used=self.agent.model_name,
                    execution_time_ms=(time.time() - start_time) * 1000
                )

        metadata = DocumentMetadata(
            document_id=doc_id,
            filename=filename,
            file_size_bytes=file_size,
            mime_type=clean_mime,
            sha256_hash=sha256,
            total_pages=1,
            processed_at=datetime.now(timezone.utc)
        )

        with trace_span(
            name="EIR Document Extraction & Checksum Audit",
            category="DOC_INTELLIGENCE",
            attributes={"document.id": doc_id, "document.filename": filename, "mime_type": clean_mime, "file_size_bytes": file_size}
        ) as span:
            # 1. Model Extraction (or deterministic mock if provided)
            extracted_data: Optional[ExtractedEIRData] = None
            if mock_extraction is not None:
                extracted_data = mock_extraction
            else:
                known_context = {}
                if expected_container_id:
                    known_context["expected_container_id"] = expected_container_id
                if expected_carrier:
                    known_context["expected_carrier"] = expected_carrier
                if default_timezone:
                    known_context["default_timezone"] = default_timezone

                extracted_data = self.agent.extract_eir(
                    document_bytes=file_bytes,
                    mime_type=clean_mime,
                    known_context=known_context if known_context else None
                )

            # 2. Deterministic Application-Level Validation
            validation_report = DocumentValidator.validate_eir_extraction(
                extracted=extracted_data,
                expected_container_id=expected_container_id,
                expected_carrier=expected_carrier,
                default_timezone=default_timezone
            )

            elapsed_ms = (time.time() - start_time) * 1000
            
            span.set_attribute("extraction.status", validation_report.status.value)
            if extracted_data:
                span.set_attribute("container_id", extracted_data.container_id or "UNKNOWN")
                span.set_attribute("iso6346_valid", validation_report.container_id_checksum_matches)

            return EIRExtractionResult(
                document_metadata=metadata,
                extraction_status=validation_report.status,
                extracted_data=extracted_data,
                validation_report=validation_report,
                model_name_used=self.agent.model_name,
                execution_time_ms=round(elapsed_ms, 2)
            )
