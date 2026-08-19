import base64
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel

from ..models.documents import (
    EIRExtractionResult,
    DocumentValidationReport,
    ExtractedEIRData
)
from ..services.document_service import DocumentIntelligenceService
from ..services.document_validator import DocumentValidator

router = APIRouter(prefix="/api/documents", tags=["Document Intelligence"])
_doc_service = DocumentIntelligenceService()


class Base64DocumentRequest(BaseModel):
    filename: str
    base64_content: str
    mime_type: str = "application/pdf"
    expected_container_id: Optional[str] = None
    expected_carrier: Optional[str] = None
    default_timezone: Optional[str] = None


class DirectValidationRequest(BaseModel):
    extracted_data: ExtractedEIRData
    expected_container_id: Optional[str] = None
    expected_carrier: Optional[str] = None
    default_timezone: Optional[str] = None


@router.post("/extract", response_model=EIRExtractionResult)
async def extract_document_multipart(
    file: UploadFile = File(...),
    expected_container_id: Optional[str] = Form(None),
    expected_carrier: Optional[str] = Form(None),
    default_timezone: Optional[str] = Form(None)
) -> EIRExtractionResult:
    """
    Ingests and extracts structured custody information from an uploaded EIR document (PDF or image).
    Applies multimodal extraction via Gemini and deterministic ISO 6346 / timestamp validation.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a valid filename.")

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    if len(file_bytes) > DocumentIntelligenceService.MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum allowed size of 25 MB.")

    mime_type = file.content_type or "application/octet-stream"

    result = _doc_service.process_document(
        file_bytes=file_bytes,
        filename=file.filename,
        mime_type=mime_type,
        expected_container_id=expected_container_id,
        expected_carrier=expected_carrier,
        default_timezone=default_timezone
    )
    return result


@router.post("/extract-base64", response_model=EIRExtractionResult)
def extract_document_base64(payload: Base64DocumentRequest) -> EIRExtractionResult:
    """
    Base64 JSON endpoint for headless pipelines or browser web workers.
    """
    try:
        file_bytes = base64.b64decode(payload.base64_content)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 payload: {str(e)}")

    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Decoded file content is empty.")

    result = _doc_service.process_document(
        file_bytes=file_bytes,
        filename=payload.filename,
        mime_type=payload.mime_type,
        expected_container_id=payload.expected_container_id,
        expected_carrier=payload.expected_carrier,
        default_timezone=payload.default_timezone
    )
    return result


@router.post("/validate", response_model=DocumentValidationReport)
def validate_extracted_eir(payload: DirectValidationRequest) -> DocumentValidationReport:
    """
    Deterministically re-validates an existing extracted EIR against case rules.
    """
    return DocumentValidator.validate_eir_extraction(
        extracted=payload.extracted_data,
        expected_container_id=payload.expected_container_id,
        expected_carrier=payload.expected_carrier,
        default_timezone=payload.default_timezone
    )
